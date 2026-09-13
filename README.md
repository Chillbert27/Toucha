TOUCHa 0.2.0-beta — streamer release (GitHub)
================================================

The Quest viewer app is distributed through the Meta Horizon Store
(search "TOUCHa"). This archive contains the Linux host side only.

Verify FIRST (needs only the public key in toucha-release.gpg):
  gpg --import toucha-release.gpg
  gpg --verify SHA256SUMS.asc
  sha256sum -c SHA256SUMS.txt
All lines must report OK / good signature. The verified fingerprint is:
  DB7A 3F89 6919 DA51 825F 3C59 715A 9113 AF69 D487
  ("TOUCHa Releases (TOUCHa release signing)")

Contents:
  toucha-streamer            Linux streamer, native binary (run with --help).
                             Recommended: correct multitouch mapping.
  com.toucha.Streamer.flatpak
                             Linux streamer, Flatpak bundle (GPG-signed
                             inside). Sandboxed; KWin touch mapping falls
                             back to default.
  toucha-release.gpg         Public release key (see verification above).

Streamer (Linux) — pick ONE:
------------------------------
Native:
  ./toucha-streamer --source portal --monitors 3 --audio system
Flatpak (verified remote — never use --no-gpg-verify):
  flatpak remote-add --user toucha-release --gpg-import=toucha-release.gpg \
      <https://github.com/Chillbert27/Toucha>
  flatpak --user install toucha-release com.toucha.Streamer
  flatpak run com.toucha.Streamer --source portal --monitors 3 --audio system
  (Single-file alternative: flatpak --user install ./com.toucha.Streamer.flatpak
   — the bundle carries the release GPG signature inside.)

Then on the Quest: install TOUCHa from the Store, pick the host, tap
Trust ONCE after comparing the SHA-256 fingerprint character by character
with the streamer log on the host. Reject = no stream, ever, until you
decide otherwise. The streamer prints its host fingerprint at every start.

Security model (short version)
------------------------------
Discovery (udp/8777) + signaling (tcp/8778+i) + identity are TLS 1.2+
with pinned fingerprints — no cleartext exists anywhere. Media is SRTP
with a fresh key per session. Internet streaming belongs inside
WireGuard (see docs/wireguard.md); Tor carries control only
(docs/tor.md). Full contract: SECURITY.md in the source tree.
