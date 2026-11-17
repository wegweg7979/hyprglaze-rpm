# hyprglaze — Fedora packaging

Fedora RPM packaging for [hyprglaze](https://github.com/slastra/hyprglaze): a Wayland
shader wallpaper daemon for Hyprland that reacts to windows, the cursor and music.
Upstream ships an Arch PKGBUILD and builds with Zig; this repository carries only the
spec that turns it into RPMs. Nothing patches upstream.

## Fedora package (COPR)

```sh
sudo dnf copr enable wegweg7979/hyprglaze
sudo dnf install hyprglaze
```

## What it builds

| Package | What it is |
|---|---|
| `hyprglaze` | The daemon at `/usr/bin/hyprglaze`, its effects (23 shaders, 24 effects — `ai-buddy` shares `buddy.frag`) and the buddy sprite under `/usr/share/hyprglaze`, plus the systemd user units `hyprglaze.service` and `hyprglaze@<monitor>.service` |

Requires `hyprland-bin >= 0.55` — the Lua-config Hyprland the daemon injects its
watcher into. Fedora has no package named `hyprland`; the Omedora COPR's
`hyprland-no-session` Provides `hyprland-bin`.

## Three Fedora-side notes

- **Zig is not in Fedora at a new enough version.** hyprglaze needs ≥ 0.17 (Fedora 45
  ships 0.16.0), so the spec takes the official Zig tarball as a second source,
  unpacks it into the build root and installs nothing from it.
- **The build needs network:** Zig fetches its one dependency (`zig-toml`) at build
  time, so the COPR project runs with `enable_net: true`, like huru-calendar and
  icloud-for-omarchy.
- **`--build-id=sha1` is passed to `zig build`.** Zig emits no GNU build-id note by
  default and Fedora's `find-debuginfo` runs with `--strict-build-id`, which aborts
  the build on such a binary. The flag makes the debuginfo package real instead.
- **`-Dcpu=x86-64-v2` is passed to `zig build`.** Zig defaults to `-Dcpu=native`, so
  the first published build compiled for the COPR *builder's* microarchitecture —
  it carried AVX-512 and died with `Illegal instruction (core dumped)` on the target
  machines, which do not have it. The level is pinned in `%global zigcpu`.

## Updating the pin

Upstream publishes no tags and no releases, so the pin is a commit:

1. edit `%global commit`, `%global shortcommit` and `%global commitdate` in
   `rpm/hyprglaze.spec`
2. run `bin/spec-sources` — it re-fetches both sources, checks that the commit really
   is the tree it claims to be, and rewrites `rpm/hyprglaze.spec.sources`
3. push; the COPR webhook rebuilds
