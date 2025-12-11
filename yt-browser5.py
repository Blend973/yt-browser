#!/usr/bin/env python3
# Optimized YT-Browser
# Version 0.8.1 - Quality Config Fixed

import os
import sys
import json
import time
import shutil
import subprocess
import hashlib
import argparse
import platform
import urllib.parse
import re
import shlex

# ==========================================
# GLOBAL CONFIGURATION & CONSTANTS
# ==========================================

CLI_NAME = os.environ.get("YT_X_APP_NAME", "yt-browser")
CLI_VERSION = "0.8.1"

# XDG Base Directory specification
XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
XDG_CACHE_HOME = os.environ.get("XDG_CACHE_HOME", os.path.join(os.path.expanduser("~"), ".cache"))
XDG_VIDEOS_DIR = os.environ.get("XDG_VIDEOS_DIR", os.path.join(os.path.expanduser("~"), "Videos"))

CLI_CONFIG_DIR = os.path.join(XDG_CONFIG_HOME, CLI_NAME)
CLI_CONFIG_FILE = os.path.join(CLI_CONFIG_DIR, f"{CLI_NAME}.conf")
CLI_CACHE_DIR = os.path.join(XDG_CACHE_HOME, CLI_NAME)
CLI_PREVIEW_IMAGES_CACHE_DIR = os.path.join(CLI_CACHE_DIR, "preview_images")
CLI_PREVIEW_SCRIPTS_DIR = os.path.join(CLI_CACHE_DIR, "preview_text")
CLI_HELPER_SCRIPT = os.path.join(CLI_CONFIG_DIR, "yt-x-helper.sh")
CLI_PREVIEW_DISPATCHER = os.path.join(CLI_CONFIG_DIR, "yt-x-preview.sh")

# Platform detection
uname = platform.uname().system.lower()
PLATFORM = "mac" if "darwin" in uname else ("windows" if "windows" in uname else "linux")

# Default Configuration
DEFAULT_CONFIG = {
    "IMAGE_RENDERER": "",
    "EDITOR": os.environ.get("EDITOR", "nano"),
    "PREFERRED_SELECTOR": "fzf",
    "VIDEO_QUALITY": "720",
    "ENABLE_PREVIEW": "false",
    "PLAYER": "mpv",
    "PREFERRED_BROWSER": "", # e.g., "chrome", "firefox"
    "NO_OF_SEARCH_RESULTS": "30",
    "NOTIFICATION_DURATION": "5",
    "SEARCH_HISTORY": "true",
    "DOWNLOAD_DIRECTORY": os.path.join(XDG_VIDEOS_DIR, CLI_NAME),
    # Persistent State Keys
    "AUDIO_ONLY_MODE": "false",
    "AUTOPLAY_MODE": "off" # off, playlist, related
}

CONFIG = DEFAULT_CONFIG.copy()

# Runtime State
PLAYLIST_START = 1
PLAYLIST_END = 30
CURRENT_TIME = int(time.time())

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def clear_screen():
    """Portable screen clear."""
    sys.stdout.write("\033c")
    sys.stdout.flush()

def check_dependencies():
    """Checks for required tools before running."""
    required = ["yt-dlp", "fzf", "jq", "curl"]
    missing = [tool for tool in required if not shutil.which(tool)]

    if not shutil.which("mpv") and not shutil.which("vlc"):
        missing.append("mpv OR vlc")

    if missing:
        print(f"Error: Missing dependencies: {', '.join(missing)}")
        print("Please install them via your package manager.")
        sys.exit(1)

def generate_sha256(text):
    if text is None: text = ""
    if isinstance(text, str): text = text.encode('utf-8')
    return hashlib.sha256(text).hexdigest()

def send_notification(message):
    sys.stderr.write(f"\033[94m[Info]\033[0m {message}\n")
    time.sleep(int(CONFIG["NOTIFICATION_DURATION"]))

def byebye(code=0):
    clear_screen()
    sys.exit(code)

def cleanup_cache():
    """Removes preview images older than 24 hours."""
    try:
        now = time.time()
        cutoff = now - 86400
        for d in [CLI_PREVIEW_IMAGES_CACHE_DIR, CLI_PREVIEW_SCRIPTS_DIR]:
            if not os.path.exists(d): continue
            for filename in os.listdir(d):
                filepath = os.path.join(d, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
    except Exception: pass

def create_bash_helpers():
    """Generates the bash scripts needed for fzf preview."""
    # 1. Helper Functions Script
    helper_content = f"""#!/usr/bin/env bash
export CLI_PREVIEW_IMAGES_CACHE_DIR="{CLI_PREVIEW_IMAGES_CACHE_DIR}"
export CLI_PREVIEW_SCRIPTS_DIR="{CLI_PREVIEW_SCRIPTS_DIR}"
export IMAGE_RENDERER="{CONFIG['IMAGE_RENDERER']}"

generate_sha256() {{
  local input
  if [ -n "$1" ]; then input="$1"; else input=$(cat); fi
  if command -v sha256sum &>/dev/null; then echo -n "$input" | sha256sum | awk '{{print $1}}'
  elif command -v shasum &>/dev/null; then echo -n "$input" | shasum -a 256 | awk '{{print $1}}'
  else echo -n "$input" | base64 | tr '/+' '_-' | tr -d '\\n'; fi
}}

fzf_preview() {{
  file=$1
  dim=${{FZF_PREVIEW_COLUMNS}}x${{FZF_PREVIEW_LINES}}
  if [ "$dim" = x ]; then dim=$(stty size </dev/tty | awk "{{print \\$2 \\"x\\" \\$1}}"); fi

  if ! [ "$IMAGE_RENDERER" = "icat" ] && [ -z "$KITTY_WINDOW_ID" ]; then
     dim=${{FZF_PREVIEW_COLUMNS}}x$((FZF_PREVIEW_LINES - 1))
  fi

  if [ "$IMAGE_RENDERER" = "icat" ] || [ -n "$KITTY_WINDOW_ID" ]; then
    if command -v kitten >/dev/null 2>&1; then
      kitten icat --clear --transfer-mode=memory --unicode-placeholder --stdin=no --place="$dim@0x0" "$file" | sed "\\$d" | sed "$(printf "\\$s/\\$/\\033[m/")"
    elif command -v icat >/dev/null 2>&1; then
      icat --clear --transfer-mode=memory --unicode-placeholder --stdin=no --place="$dim@0x0" "$file" | sed "\\$d" | sed "$(printf "\\$s/\\$/\\033[m/")"
    else
      kitty icat --clear --transfer-mode=memory --unicode-placeholder --stdin=no --place="$dim@0x0" "$file" | sed "\\$d" | sed "$(printf "\\$s/\\$/\\033[m/")"
    fi
  elif command -v chafa >/dev/null 2>&1; then
    chafa -s "$dim" "$file"; echo
  elif command -v imgcat >/dev/null; then
    imgcat -W "${{dim%%x*}}" -H "${{dim##*x}}" "$file"
  else
    echo "No image renderer found"
  fi
}}
export -f generate_sha256
export -f fzf_preview
"""
    with open(CLI_HELPER_SCRIPT, 'w') as f: f.write(helper_content)
    os.chmod(CLI_HELPER_SCRIPT, 0o755)

    # 2. Preview Dispatcher Script
    preview_content = f"""#!/usr/bin/env bash
source "{CLI_HELPER_SCRIPT}"
MODE="$1"; shift; SELECTION="$*"

if [ "$MODE" = "video" ]; then
  title="$SELECTION"
  # Remove the numbering (e.g. "01 ") before hashing
  clean_title=$(echo "$title" | sed -E 's/^[0-9]+ //g')
  id=$(generate_sha256 "$clean_title")
  if [ -f "{CLI_PREVIEW_SCRIPTS_DIR}/${{id}}.txt" ]; then
    . "{CLI_PREVIEW_SCRIPTS_DIR}/${{id}}.txt"
  else
    echo "Loading Preview..."
  fi
fi
"""
    with open(CLI_PREVIEW_DISPATCHER, 'w') as f: f.write(preview_content)
    os.chmod(CLI_PREVIEW_DISPATCHER, 0o755)

def save_config():
    """Writes the current CONFIG dictionary to file."""
    try:
        with open(CLI_CONFIG_FILE, 'w') as f:
            for key, value in CONFIG.items():
                f.write(f"{key}: {value}\n")
    except Exception as e:
        sys.stderr.write(f"Warning: Could not save config: {e}\n")

def load_config():
    global CONFIG, PLAYLIST_END

    # Ensure directories
    for d in [CLI_CONFIG_DIR, CLI_PREVIEW_IMAGES_CACHE_DIR, CLI_PREVIEW_SCRIPTS_DIR]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(CLI_CONFIG_FILE):
        save_config() # Write defaults

    with open(CLI_CONFIG_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                CONFIG[key] = value

    # Auto-detect renderer if missing
    if not CONFIG["IMAGE_RENDERER"]:
        CONFIG["IMAGE_RENDERER"] = "icat" if os.environ.get("KITTY_WINDOW_ID") else "chafa"

    # Format browser args
    if CONFIG["PREFERRED_BROWSER"] and "--cookies-from-browser" not in CONFIG["PREFERRED_BROWSER"]:
        CONFIG["PREFERRED_BROWSER"] = f"--cookies-from-browser {CONFIG['PREFERRED_BROWSER']}"

    # Expand paths
    CONFIG["DOWNLOAD_DIRECTORY"] = os.path.expandvars(os.path.expanduser(CONFIG["DOWNLOAD_DIRECTORY"]))
    if not os.path.exists(CONFIG["DOWNLOAD_DIRECTORY"]):
        os.makedirs(CONFIG["DOWNLOAD_DIRECTORY"], exist_ok=True)

    PLAYLIST_END = int(CONFIG["NO_OF_SEARCH_RESULTS"])
    create_bash_helpers()
    cleanup_cache()

    # Set FZF Environment
    os.environ["FZF_DEFAULT_OPTS"] = os.environ.get("YT_X_FZF_OPTS", """
    --color=fg:#d0d0d0,fg+:#d0d0d0,bg:#121212,bg+:#262626
    --color=hl:#5f87af,hl+:#5fd7ff,info:#afaf87,marker:#87ff00
    --color=prompt:#d7005f,spinner:#af5fff,pointer:#af5fff,header:#87afaf
    --color=border:#262626,label:#aeaeae,query:#d9d9d9
    --border="rounded" --border-label="" --preview-window="border-rounded" --prompt="> "
    --marker=">" --pointer="◆" --separator="─" --scrollbar="│"
    """)
    os.environ["PLATFORM"] = PLATFORM
    os.environ["IMAGE_RENDERER"] = CONFIG["IMAGE_RENDERER"]

def prompt(text, value=""):
    history_file = os.path.join(CLI_CACHE_DIR, "search_history.txt")
    history_text = ""
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                lines = [l.strip() for l in f if l.strip()]
            lines = lines[-10:]
            lines.reverse()
            history_formatted = "\n".join([f"{i+1}. {l}" for i, l in enumerate(lines)])
            history_text = f"Search history:\n{history_formatted}\n(Enter !<n> to select from history. Example: !1)\n"
        except Exception: pass

    if CONFIG["PREFERRED_SELECTOR"] == "rofi":
        cmd = ["rofi", "-dmenu", "-p", f"{text}: "]
        if CONFIG["SEARCH_HISTORY"] == "true" and history_text:
             cmd.extend(["-mesg", history_text])
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = proc.communicate(input="")
        return out.strip()
    elif shutil.which("gum"):
        if CONFIG["SEARCH_HISTORY"] == "true" and history_text: text += "\n" + history_text
        cmd = ["gum", "input", "--header", "", "--prompt", f"{text}: ", "--value", value]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        return proc.stdout.strip()
    else:
        if CONFIG["SEARCH_HISTORY"] == "true" and history_text: sys.stderr.write(f"{history_text}\n")
        sys.stderr.write(f"{text}: ")
        sys.stderr.flush()
        try: return input().strip()
        except EOFError: return ""

def launcher(options_str, prompt_text, preview_mode=None):
    selector = CONFIG["PREFERRED_SELECTOR"].lower()
    if selector == "rofi":
        cmd = ["rofi", "-sort", "-matching", "fuzzy", "-dmenu", "-i", "-p", "", "-mesg", prompt_text, "-matching", "fuzzy", "-sorting-method", "fzf"]
        if CONFIG.get("ROFI_THEME"): cmd[1:1] = ["-no-config", "-theme", CONFIG["ROFI_THEME"]]
        else: cmd.extend(["-width", "1500"])
        clean_options = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', options_str)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = proc.communicate(input=clean_options)
        res = out.strip()
        return res if res else "Exit"
    else: # fzf
        cmd = ["fzf", "--info=hidden", "--layout=reverse", "--height=100%", f"--prompt={prompt_text}: ",
            "--header-first", "--header=", "--exact", "--cycle", "--ansi"]
        if preview_mode:
            cmd.extend(["--preview-window=left,35%,wrap", "--bind=right:accept", "--expect=shift-left,shift-right",
                "--tabstop=1", f"--preview=bash '{CLI_PREVIEW_DISPATCHER}' '{preview_mode}' {{}}"])
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        out, _ = proc.communicate(input=options_str)
        lines = out.splitlines()
        if not lines: return ""
        if preview_mode and len(lines) >= 2: return lines[1]
        return lines[0]

def run_yt_dlp(url, extra_args=None):
    cmd = ["yt-dlp", url, "-J", "--flat-playlist", "--extractor-args", "youtubetab:approximate_date",
           "--playlist-start", str(PLAYLIST_START), "--playlist-end", str(PLAYLIST_END)]
    if CONFIG["PREFERRED_BROWSER"]: cmd.extend(shlex.split(CONFIG["PREFERRED_BROWSER"]))
    if extra_args: cmd.extend(extra_args)

    if shutil.which("gum"):
        spin_cmd = ["gum", "spin", "--show-output", "--"] + cmd
        proc = subprocess.run(spin_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    else:
        sys.stderr.write("Loading...\n")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if proc.returncode != 0:
        send_notification("Failed to fetch data. Check connection or update yt-dlp.")
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        # Attempt to recover JSON from mixed output
        try:
            output = proc.stdout
            json_start = output.find('{')
            if json_start != -1:
                return json.loads(output[json_start:])
        except: pass
        send_notification("Failed to parse API response.")
        return None

# ==========================================
# PREVIEW GENERATION
# ==========================================

def generate_text_preview(data):
    if not data or "entries" not in data: return
    for i, video in enumerate(data["entries"]):
        if not video: continue
        raw_title = video.get("title", "")
        # Sanitize: remove newlines and leading numbers for hash consistency
        clean_title = re.sub(r'^[0-9]+ ', '', raw_title).replace('\n', ' ')
        filename_hash = generate_sha256(clean_title)

        # Safe quoting for bash injection
        safe_title = shlex.quote(clean_title)

        thumbs = video.get("thumbnails", [])
        thumb_url = thumbs[-1]["url"] if thumbs else ""
        preview_image_hash = generate_sha256(thumb_url)

        vc = video.get("view_count")
        view_count = "{:,}".format(int(vc)) if vc is not None else "Unknown"
        ls = video.get("live_status")
        live_status = "Online" if ls == "is_live" else ("Offline" if ls == "was_live" else "False")

        desc = video.get("description") or "null"
        safe_description = shlex.quote(desc.replace('\n', ' ').replace('\r', ' '))
        safe_channel = shlex.quote(video.get("channel", ""))

        dur = video.get("duration")
        duration_str = "Unknown"
        if dur:
            try:
                dur = float(dur)
                if dur >= 3600: duration_str = f"{int(dur // 3600)} hours"
                elif dur >= 60: duration_str = f"{int(dur // 60)} mins"
                else: duration_str = f"{int(dur)} secs"
            except: pass

        ts = video.get("timestamp")
        timestamp_str = ""
        if ts:
            try:
                diff = CURRENT_TIME - int(ts)
                if diff < 60: timestamp_str = "just now"
                elif diff < 3600: timestamp_str = f"{diff // 60} minutes ago"
                elif diff < 86400: timestamp_str = f"{diff // 3600} hours ago"
                elif diff < 604800: timestamp_str = f"{diff // 86400} days ago"
                elif diff < 2635200: timestamp_str = f"{diff // 604800} weeks ago"
                elif diff < 31622400: timestamp_str = f"{diff // 2635200} months ago"
                else: timestamp_str = f"{diff // 31622400} years ago"
            except: pass

        content = f"""
if [ -f "{CLI_PREVIEW_IMAGES_CACHE_DIR}/{preview_image_hash}.jpg" ];then fzf_preview "{CLI_PREVIEW_IMAGES_CACHE_DIR}/{preview_image_hash}.jpg" 2>/dev/null;
else echo loading preview image...;
fi
ll=1
while [ $ll -le $FZF_PREVIEW_COLUMNS ];do echo -n -e "─" ;(( ll++ ));done;
echo
echo {safe_title}
ll=1
while [ $ll -le $FZF_PREVIEW_COLUMNS ];do echo -n -e "─" ;(( ll++ ));done;
echo "Channel: {safe_channel}"
echo "Duration: {duration_str}"
echo "View Count: {view_count} views"
echo "Live Status: {live_status}"
echo "Uploaded: {timestamp_str}"
ll=1
while [ $ll -le $FZF_PREVIEW_COLUMNS ];do echo -n -e "─" ;(( ll++ ));done;
echo
! [ {safe_description} = "null" ] && echo -n {safe_description};
"""
        with open(os.path.join(CLI_PREVIEW_SCRIPTS_DIR, f"{filename_hash}.txt"), "w") as f: f.write(content)

def download_preview_images(data, prefix=""):
    if not data or "entries" not in data: return
    generate_text_preview(data)
    previews_file = os.path.join(CLI_PREVIEW_IMAGES_CACHE_DIR, "previews.txt")
    if os.path.exists(previews_file): os.remove(previews_file)
    entries_to_download = []
    for video in data["entries"]:
        if not video: continue
        thumbs = video.get("thumbnails", [])
        if not thumbs: continue
        url = thumbs[-1]["url"]
        filename = generate_sha256(url)
        if not os.path.exists(os.path.join(CLI_PREVIEW_IMAGES_CACHE_DIR, f"{filename}.jpg")):
            entries_to_download.append((url, filename))

    if entries_to_download:
        with open(previews_file, "w") as f:
            for url, filename in entries_to_download:
                f.write(f'url = "{prefix}{url}"\n')
                f.write(f'output = "{CLI_PREVIEW_IMAGES_CACHE_DIR}/{filename}.jpg"\n')
        subprocess.Popen(["curl", "-s", "-K", previews_file], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

# ==========================================
# CORE LOGIC
# ==========================================

def playlist_explorer(search_results, url):
    global PLAYLIST_START, PLAYLIST_END

    # Load persistent state
    audio_only_mode = CONFIG["AUDIO_ONLY_MODE"].lower() == "true"
    autoplay_mode = CONFIG["AUTOPLAY_MODE"]

    download_images = False

    while True:
        if not search_results or "entries" not in search_results: break
        entries = search_results.get("entries", [])
        titles = []

        if not download_images:
            for i, entry in enumerate(entries):
                if not entry: continue
                num = str(i + 1)
                if len(entries) < 10 and len(num) < 2: num = "0" + num
                clean_t = entry.get('title', '').replace('\n', ' ')
                entry["title"] = f"{num} {clean_t}"
                titles.append(entry["title"])
        else:
            for entry in entries:
                if entry: titles.append(entry.get("title", "").replace('\n', ' '))

        if CONFIG["ENABLE_PREVIEW"] == "true" and CONFIG["PREFERRED_SELECTOR"] == "fzf" and not download_images:
            download_preview_images(search_results)
            download_images = True

        if CONFIG["ENABLE_PREVIEW"] == "true":
            options_str = "\n".join(titles) + f"\nNext\nPrevious\nBack\nExit"
            selection = launcher(options_str, "select video", "video")
        else:
            options_str = "\n".join(titles + ["Next", "Previous", "Back", "Exit"])
            selection = launcher(options_str, "select video")

        selection = re.sub(r'^[^0-9]*  ', '', selection)
        clear_screen()

        if selection == "Next":
            PLAYLIST_START += int(CONFIG["NO_OF_SEARCH_RESULTS"])
            PLAYLIST_END += int(CONFIG["NO_OF_SEARCH_RESULTS"])
            search_results = run_yt_dlp(url)
            download_images = False
            continue
        elif selection == "Previous":
            PLAYLIST_START -= int(CONFIG["NO_OF_SEARCH_RESULTS"])
            if PLAYLIST_START <= 0: PLAYLIST_START = 1
            PLAYLIST_END -= int(CONFIG["NO_OF_SEARCH_RESULTS"])
            min_end = int(CONFIG["NO_OF_SEARCH_RESULTS"])
            if PLAYLIST_END < min_end: PLAYLIST_END = min_end
            search_results = run_yt_dlp(url)
            download_images = False
            continue
        elif selection in ["Back", "", "Exit"]:
            if selection == "Exit": byebye()
            break

        try:
            sel_id = int(selection.split(' ')[0])
            current_index = sel_id - 1
            video = entries[current_index]
            clean_title = re.sub(r'^[0-9]+ ', '', video['title'])
        except (ValueError, IndexError): continue

        # Action Menu Loop
        while True:
            audio_state = "[x]" if audio_only_mode else "[ ]"

            autoplay_label = "[Off]"
            if autoplay_mode == "playlist": autoplay_label = "[Playlist]"
            elif autoplay_mode == "related": autoplay_label = "[Related]"

            media_actions = [
                f"Watch",
                f"Toggle Audio Only {audio_state}",
                f"Toggle Autoplay {autoplay_label}",
                f"Download",
                f"Back", f"Exit"
            ]

            action_sel = launcher("\n".join(media_actions), "Select Media Action")
            clear_screen()

            if action_sel == "Exit": byebye()
            if action_sel in ["Back", ""]: break

            if "Toggle Audio Only" in action_sel:
                audio_only_mode = not audio_only_mode
                CONFIG["AUDIO_ONLY_MODE"] = str(audio_only_mode).lower()
                save_config()
                continue

            if "Toggle Autoplay" in action_sel:
                modes = ["off", "playlist", "related"]
                curr_idx = modes.index(autoplay_mode)
                autoplay_mode = modes[(curr_idx + 1) % len(modes)]
                CONFIG["AUTOPLAY_MODE"] = autoplay_mode
                save_config()
                continue

            vid_url = video.get("url")

            if action_sel == "Watch":
                # Autoplay Loop
                while True:
                    print(f"Now playing: {clean_title}")

                    player_cmd = [CONFIG["PLAYER"], vid_url]
                    if CONFIG["PLAYER"] == "mpv":
                        if audio_only_mode:
                            player_cmd.extend(["--no-video", "--force-window=no"])
                        elif CONFIG["VIDEO_QUALITY"].isdigit():
                            # FIX 1: Apply format selection to MPV
                            q = CONFIG["VIDEO_QUALITY"]
                            player_cmd.append(f"--ytdl-format=bestvideo[height<={q}]+bestaudio/best[height<={q}]/best")

                    elif CONFIG["PLAYER"] == "vlc":
                        player_cmd.extend(["--video-title", clean_title])
                        if audio_only_mode: player_cmd.append("--no-video")

                    try:
                        # Run player
                        proc = subprocess.run(player_cmd)

                        # If player failed (non-zero exit), stop autoplay
                        if proc.returncode != 0:
                            print("Player exited with error. Stopping autoplay.")
                            break

                        if autoplay_mode == "off":
                            break

                    except KeyboardInterrupt:
                        print("\nStopping playback...")
                        break

                    # Handle Autoplay Logic
                    if autoplay_mode == "playlist":
                        current_index += 1
                        if current_index >= len(entries):
                            print("End of current list. Fetching next page...")
                            PLAYLIST_START += int(CONFIG["NO_OF_SEARCH_RESULTS"])
                            PLAYLIST_END += int(CONFIG["NO_OF_SEARCH_RESULTS"])
                            search_results = run_yt_dlp(url)
                            if not search_results or "entries" not in search_results: break
                            entries = search_results.get("entries", [])
                            current_index = 0
                            download_images = False

                        if current_index < len(entries):
                            video = entries[current_index]
                            vid_url = video.get("url")
                            clean_title = re.sub(r'^[0-9]+ ', '', video.get("title", "Unknown"))
                        else: break

                    elif autoplay_mode == "related":
                        print("Fetching related video...")
                        vid_id = video.get("id")
                        mix_url = f"https://www.youtube.com/watch?v={vid_id}&list=RD{vid_id}"
                        mix_cmd = ["yt-dlp", mix_url, "-J", "--flat-playlist",
                                  "--playlist-start", "1", "--playlist-end", "5"]
                        if CONFIG["PREFERRED_BROWSER"]: mix_cmd.extend(shlex.split(CONFIG["PREFERRED_BROWSER"]))

                        proc = subprocess.run(mix_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                        try:
                            mix_data = json.loads(proc.stdout)
                            found_next = False
                            if mix_data and "entries" in mix_data:
                                for entry in mix_data["entries"]:
                                    if entry.get("id") != vid_id:
                                        video = entry
                                        vid_url = video.get("url")
                                        clean_title = video.get("title")
                                        found_next = True
                                        break
                            if not found_next:
                                print("No related videos found.")
                                break
                        except:
                            print("Failed to fetch related videos.")
                            break

                # Return to list after watching
                break

            elif action_sel == "Download":
                folder = "audio" if audio_only_mode else "videos"
                # FIX 2: Apply format selection to Download
                if audio_only_mode:
                    ext_args = ["-x", "-f", "bestaudio", "--audio-format", "mp3"]
                else:
                    q = CONFIG["VIDEO_QUALITY"]
                    ext_args = ["-f", f"bestvideo[height<={q}]+bestaudio/best[height<={q}]/best"] if q.isdigit() else []

                out_tmpl = os.path.join(CONFIG["DOWNLOAD_DIRECTORY"], f"{folder}/individual/%(channel)s/%(title)s.%(ext)s")

                cmd = ["yt-dlp", vid_url, "--output", out_tmpl] + ext_args
                if CONFIG["PREFERRED_BROWSER"]: cmd.extend(shlex.split(CONFIG["PREFERRED_BROWSER"]))

                subprocess.Popen(cmd, start_new_session=True)
                send_notification(f"Started downloading {clean_title}")

    PLAYLIST_START = 1
    PLAYLIST_END = int(CONFIG["NO_OF_SEARCH_RESULTS"])

def main_menu(initial_action=None, search_term=None):
    clear_screen()
    action = initial_action
    if not action:
        options = [
            f"Search",
            f"Edit Config",
            f"Exit"
        ]
        sel = launcher("\n".join(options), "Select Action")
        action = re.sub(r'.*  ', '', sel)

    if action == "Exit": byebye()

    elif action == "Search":
        clear_screen()
        if not search_term:
            search_term = prompt("Enter term to search for")
            if re.match(r'^![0-9]{1,2}$', search_term):
                idx = int(search_term[1:])
                hist_file = os.path.join(CLI_CACHE_DIR, "search_history.txt")
                if os.path.exists(hist_file):
                    try:
                        with open(hist_file) as f: lines = [l.strip() for l in f if l.strip()]
                        if lines and idx <= 10: search_term = lines[-idx]
                    except Exception: pass

        if not search_term: return main_menu()

        sp = "EgIQAQ%253D%253D" # Default video
        match = re.match(r'^(:[a-z]+)\s+(.+)', search_term)
        if match:
            filter_cmd, search_term = match.groups()
            if filter_cmd == ":hour": sp="EgIIAQ%253D%253D"
            elif filter_cmd == ":today": sp="EgIIAg%253D%253D"
            elif filter_cmd == ":week": sp="EgIIAw%253D%253D"
            elif filter_cmd == ":month": sp="EgIIBA%253D%253D"
            elif filter_cmd == ":year": sp="EgIIBQ%253D%253D"

        if CONFIG["SEARCH_HISTORY"] == "true":
            hist_file = os.path.join(CLI_CACHE_DIR, "search_history.txt")
            lines = []
            if os.path.exists(hist_file):
                try:
                    with open(hist_file) as f: lines = [l.strip() for l in f if l.strip() and l.strip() != search_term]
                except Exception: pass
            lines.append(search_term)
            with open(hist_file, 'w') as f: f.write("\n".join(lines) + "\n")

        term_enc = urllib.parse.quote(search_term)
        url = f"https://www.youtube.com/results?search_query={term_enc}&sp={sp}"
        playlist_explorer(run_yt_dlp(url), url)

    elif action == "Edit Config":
        subprocess.run([CONFIG["EDITOR"], CLI_CONFIG_FILE])
        load_config()

    main_menu()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Browse youtube from the terminal ({CLI_NAME})")
    parser.add_argument("-S", "--search", help="search for a video")
    parser.add_argument("-e", "--edit-config", action="store_true", help="edit config file")
    parser.add_argument("-v", "--version", action="store_true")
    args, unknown = parser.parse_known_args()

    if args.version:
        print(f"{CLI_NAME} v{CLI_VERSION}")
        sys.exit(0)

    check_dependencies()
    load_config()

    if args.edit_config:
        subprocess.run([CONFIG["EDITOR"], CLI_CONFIG_FILE])
        sys.exit(0)

    try:
        if args.search: main_menu(initial_action="Search", search_term=args.search)
        else: main_menu()
    except KeyboardInterrupt:
        byebye()
