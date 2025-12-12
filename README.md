# YT-Browser: Browse YouTube from Your Terminal

YT-Browser is a powerful command-line tool that lets you search, browse, watch, and download YouTube videos directly from your terminal. It's designed for keyboard-driven navigation, providing a fast and efficient YouTube experience without ever leaving your command line.

## Features

- **Interactive Search**: Search for YouTube videos and browse results interactively.
- **Terminal Previews**: Get video thumbnail previews directly in compatible terminals (e.g., Kitty, using Chafa).
- **Flexible Playback**: Play videos (or just the audio) in your preferred player like `mpv` or `vlc`.
- **Autoplay Support**: Automatically play the next video in a playlist or related videos.
- **Download Videos**: Download videos or audio for offline access.
- **Search Filters**: Filter search results by upload date (e.g., today, this week, this year).
- **Search History**: Quickly access your past searches.
- **Customizable**: Configure players, selectors, video quality, and more through a simple config file.
- **Multiple Selectors**: Choose between `fzf` (default), `rofi`, or `gum` for menus and prompts.

## Dependencies

You'll need to install a few command-line tools for YT-Browser to work.

#### Core Dependencies:
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**: The core engine for fetching video data.
- **[fzf](https://github.com/junegunn/fzf)**: The default interactive menu for browsing videos.
- **[jq](https://stedolan.github.io/jq/)**: A command-line JSON processor.
- **[curl](https://curl.se/)**: Used for downloading thumbnail previews.
- **A Video Player**: `mpv` (recommended) or `vlc`.

#### Optional Dependencies:
- **For Image Previews**:
    - `chafa` (recommended for most terminals)
    - `kitty-icat` (if you use Kitty terminal)
    - `imgcat` (for iTerm2 users)
- **Alternative Menus**:
    - `rofi`
    - `gum`

### Installation of Dependencies

<details>
<summary><b>On Debian / Ubuntu</b></summary>

```bash
sudo apt update
sudo apt install -y yt-dlp fzf jq curl mpv chafa
```
</details>

<details>
<summary><b>On Arch Linux</b></summary>

```bash
sudo pacman -Sy yt-dlp fzf jq curl mpv chafa
```
</details>

<details>
<summary><b>On macOS (using Homebrew)</b></summary>

```bash
brew install yt-dlp fzf jq curl mpv chafa
```
</details>

## Installation

1.  **Download the script**:
    ```bash
    curl -o yt-browser.py https://raw.githubusercontent.com/Blend973/yt-browser/main/yt-browser.py
    ```
    
2.  **Make it executable**:
    ```bash
    chmod +x yt-browser.py
    ```

3.  **Move it to your PATH**:
    Move the script to a directory in your system's `PATH` to make it accessible from anywhere. A common choice is `/usr/local/bin`.
    ```bash
    sudo mv yt-browser.py /usr/local/bin/yt-browser
    ```

## Usage

Once installed, you can run the script with the `yt-browser` command.

- **Run interactively**:
  ```bash
  yt-browser
  ```
- **Search directly**:
  ```bash
  yt-browser --search "your search query"
  ```
- **Edit the configuration file**:
  ```bash
  yt-browser --edit-config
  ```

### Search Filters
You can prefix your search query with a filter to narrow down results by upload date:
- `:hour <query>`
- `:today <query>`
- `:week <query>`
- `:month <query>`
- `:year <query>`

### Keybindings (in fzf mode)
- **Enter**: Select an item.
- **Arrow Keys**: Navigate up and down.
- **Shift-Right**: Accept the current selection and move to the action menu.
- **Shift-Left**: Go back.
- **Ctrl-C**: Exit the application.

## Configuration

The first time you run YT-Browser, it will create a configuration file at `~/.config/yt-browser/yt-browser.conf`.

You can edit this file to customize the script's behavior. Use the `--edit-config` flag to open it in your default editor.

Key configuration options include:
- `PLAYER`: Set your preferred video player (`mpv`, `vlc`).
- `PREFERRED_SELECTOR`: Change the menu system (`fzf`, `rofi`).
- `VIDEO_QUALITY`: Set the preferred video quality for playback and downloads (e.g., `720`, `1080`).
- `ENABLE_PREVIEW`: Set to `true` to enable thumbnail previews.
- `DOWNLOAD_DIRECTORY`: The path where videos and audio will be saved.
- `AUTOPLAY_MODE`: Change autoplay behavior (`off`, `playlist`, `related`).
