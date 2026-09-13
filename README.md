TOUCHaDESKTOP 0.2.0-beta — install
===================================

You need: a Linux PC (Wayland) + the TOUCHa app from the Meta Horizon
Store on your Quest. This download is the Linux host side only.

1. Verify the download (public key included):
  gpg --import toucha-release.gpg
  gpg --verify SHA256SUMS.asc
  sha256sum -c SHA256SUMS.txt
All files must report OK / good signature. Key fingerprint:
  DB7A 3F89 6919 DA51 825F 3C59 715A 9113 AF69 D487

2. Install — pick ONE:
A) Native binary:
  chmod +x TOUCHaDESKTOP
  ./TOUCHaDESKTOP --source portal --monitors 3 --audio system
B) Flatpak bundle file:
  flatpak --user install ./com.toucha.Streamer.flatpak
  flatpak run com.toucha.Streamer --source portal --monitors 3 --audio system

3. Connect on the Quest: open TOUCHa, pick your PC, compare the
SHA-256 fingerprint shown on the Quest with the one printed in the
streamer log on your PC, then tap Trust ONCE.

Options: ./TOUCHaDESKTOP --help
