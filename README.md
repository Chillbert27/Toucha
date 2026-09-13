TOUCHaDESKTOP 0.2.5-beta — install
===================================

You need: a Linux PC (Wayland) + the TOUCHa app from the Meta Horizon
Store on your Quest. This download is the Linux host side only.
The control GUI shows its version in the title bar and next to the status.

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
No terminal, no flags needed. The lower half of the window is the
streamer log (drag the divider to resize it).

Alternative: Flatpak bundle (sandboxed, same GUI via start menu):
  flatpak --user install ./com.toucha.Streamer.flatpak
Shared dependencies (KDE runtime + PyQt) come from Flathub automatically.

4. Connect on the Quest: open TOUCHa, pick your PC, compare the
SHA-256 fingerprint shown on the Quest with the one printed in the
streamer log in the GUI, then tap Trust ONCE.
