TOUCHaDESKTOP 0.2.8-beta — install
===================================

You need: a Linux PC (Wayland) + the TOUCHa app from the Meta Horizon
Store on your Quest. This download is the Linux host side only.
The control GUI (dark grey, autumn buttons) shows its version in the
title bar and next to the status.

1. Verify the download (public key included):
  gpg --import toucha-release.gpg
  gpg --verify SHA256SUMS.asc
  sha256sum -c SHA256SUMS.txt
All files must report OK / good signature. Key fingerprint:
  DB7A 3F89 6919 DA51 825F 3C59 715A 9113 AF69 D487

2. Install:
  ./install.sh
This adds TOUCHaDESKTOP to the start menu. No sudo needed.
To remove it again: ./install.sh --uninstall

 3. Start: open TOUCHaDESKTOP from the start menu and press Start.
No terminal, no flags needed. A splash screen appears for 3 seconds,
then the control GUI opens. The streamer log lives in its own Log tab;
the exact start command is shown under Advanced → Command.

Alternative: Flatpak bundle (sandboxed, same GUI via start menu):
  flatpak --user install ./com.toucha.Streamer.flatpak
Shared dependencies (KDE runtime + PyQt) come from Flathub automatically.

4. Connect on the Quest: open TOUCHa, pick your PC, compare the
SHA-256 fingerprint shown on the Quest with the one printed in the
streamer log in the GUI, then tap Trust ONCE.

5. Pick a host on the Quest (host list):
- The Welcome screen lists every TOUCHa host on your LAN as
  "name (ip) — N monitors". Tap one to stream it.
- First connect shows a Trust dialog: compare the SHA-256 fingerprint
  with the streamer log, then tap Trust ONCE. It is pinned from then on.
- Host key changed (reinstall)? Long-press the host row, tap Forget,
  reconnect and trust the new fingerprint.
- No host found? Check the streamer runs with discovery on (default),
  then Rescan. Manual address also works: IP, port (default 8778),
  monitors blank = all offered.
- Behind Tor/VPN: enable the SOCKS proxy row (e.g. Orbot) before
  connecting.
- Speaker button (♪) mutes host audio on all windows; the toolbar host
  button switches host per window (long-press = forget pin).

0.2.8 changes: Flatpak audio fixed (host sound streams again without a
system Opus library); Quest host list documented above.
