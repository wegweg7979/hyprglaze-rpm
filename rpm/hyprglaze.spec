# hyprglaze.spec — Fedora packaging for the Hyprland shader wallpaper daemon.
#
# Upstream (github.com/slastra/hyprglaze, MIT) ships an Arch PKGBUILD and a
# systemd-user-unit install; this repository carries only the spec that turns it
# into RPMs. Nothing here patches upstream: `zig build --prefix` is the whole
# install, and the build below is upstream's own invocation.
#
# Three Fedora-side facts shaped this spec, all measured on Fedora 45:
#
#   * Upstream publishes NO tags and NO releases, so Source0 is the archive of a
#     pinned commit and Version: is upstream's own `build.zig.zon` version. The
#     release string carries the commit date and short hash (the same shape the
#     omedora spec uses for its untagged snapshots).
#
#   * hyprglaze needs Zig >= 0.17 (its build.zig.zon says so and build.zig uses
#     0.17-only API: addTranslateC, addPassthruArgs). Fedora 45 ships zig 0.16.0,
#     so the toolchain is a second Source — the official upstream tarball, not a
#     Fedora package. It is unpacked in %prep and put on PATH; nothing from it is
#     installed.
#
#   * The build is NOT hermetic: Zig fetches the one dependency in
#     build.zig.zon (zig-toml) over the network at build time, so the COPR
#     project must have network access enabled (`enable_net: true`) — the same
#     requirement as huru-calendar's Go build and icloud-for-omarchy's cargo
#     build. If that policy ever changes the fix is vendoring the Zig package
#     cache alongside the spec, not patching upstream.
#
# Debug info: Zig's ReleaseSafe output carries DWARF (measured: 8 .debug_*
# sections) but, unlike every other toolchain in this fleet, no GNU build-id note
# — `--build-id` defaults to `none`. Fedora's find-debuginfo runs with
# --strict-build-id and terminates the build on such a binary ("No build ID note
# found in .../usr/bin/hyprglaze"), which is exactly what happened on the first
# COPR-shaped build of this spec. Zig's build system accepts a global
# --build-id, so the build lines below pass `--build-id=sha1`: measured to be
# accepted by `zig build` (an invalid option exits 1) and to put a proper
# .note.gnu.build-id in the artifact, so upstream needs no patch and the
# debuginfo package is real rather than skipped.

%global commit      fdafdcfe3fd9a55fd08a7be3e0973f46427c33fc
%global shortcommit fdafdcf
%global commitdate  20261110
%global zigversion  0.17.1

Name:           hyprglaze
Version:        0.1.0
Release:        2.%{commitdate}git%{shortcommit}%{?dist}
Summary:        Shader wallpaper daemon for Hyprland that reacts to windows, cursor and music

License:        MIT
URL:            https://github.com/slastra/hyprglaze

# Commit archive, not a tag archive (upstream has no tags). GitHub unpacks it to
# hyprglaze-<commit>/ — hence the -n below. bin/spec-sources pins both hashes.
Source0:        %{url}/archive/%{commit}/%{name}-%{commit}.tar.gz
# The Zig toolchain this build needs, which Fedora does not package at a new
# enough version. Official upstream build, pinned by hash like any other source.
Source1:        https://ziglang.org/download/%{zigversion}/zig-x86_64-linux-%{zigversion}.tar.xz

# Compiled for x86_64 — the only arch the hurunagus images target.
ExclusiveArch:  x86_64

# wayland-devel supplies the wayland-client and wayland-egl libraries AND
# wayland-scanner, which build.zig runs over the four vendored protocol XMLs.
BuildRequires:  wayland-devel
# Measured: libglvnd-devel is what ships BOTH /usr/lib64/libEGL.so and
# /usr/lib64/libGLESv2.so (there is no mesa-libGLES-devel on Fedora 45); Mesa
# provides the implementations and the egl.pc that the link needs.
BuildRequires:  libglvnd-devel
BuildRequires:  mesa-libEGL-devel
# libpulse-simple and libpulse: the audio-reactive effects read the output
# monitor through PipeWire's PulseAudio compatibility.
BuildRequires:  pulseaudio-libs-devel
# Upstream's own stb dependency: src/stb_image_impl.c includes <stb/stb_image.h>,
# and Fedora ships that path in stb-devel (not a bundled copy).
BuildRequires:  stb-devel
# Zig's own clang compiles the C bits, but the C library and crt objects the
# native-gnu link resolves against come from the toolchain gcc pulls in.
BuildRequires:  gcc
# Unpacking Source1, and the git client Zig uses for its git+ dependency URL.
BuildRequires:  xz
BuildRequires:  git
# The systemd user unit directory macro below, for the two units upstream ships.
BuildRequires:  systemd-rpm-macros

# Hyprland, which the daemon talks to over socket2 and into whose Lua VM it
# installs its watcher. 0.55 is upstream's floor (the Lua config manager; against
# a classic hyprland.conf the daemon refuses to start). Fedora has no package
# called `hyprland`: the COPR this image uses ships hyprland-no-session, which
# Provides hyprland-bin.
Requires:       hyprland-bin >= 0.55
# Upstream's optdepends. Only the ai-buddy effect needs it (AWS Bedrock).
Recommends:     awscli2

%description
hyprglaze renders GLSL shaders on Hyprland's background layer, and the wallpaper
knows what is happening above it: window geometry, focus, cursor position and
system audio feed the effects in real time.

It draws behind all windows through wlr-layer-shell (one instance per monitor),
uses Shadertoy-compatible uniforms, follows windows through Hyprland's own move
and resize animations including interactive drags, and ships 24 effects and 367
Gogh colour schemes. Effects that need one run real simulations: substepped
ball physics with windows as moving colliders, laser ray tracing, reaction-
diffusion coral, a MilkDrop-style visualizer and more.

State is pushed from a small Lua watcher installed inside the compositor, so it
tracks windows mid-drag instead of polling the IPC socket.

%prep
%autosetup -n %{name}-%{commit}

# The Zig toolchain, unpacked beside the source tree (it unpacks to
# zig-x86_64-linux-%{zigversion}/, which is what PATH below points at).
tar -xJf %{SOURCE1} -C %{_builddir}

# CPU baseline: Zig's standardTargetOptions defaults to -Dcpu=native, so a
# COPR-shaped build compiles for the BUILDER's microarchitecture. Measured on the
# first published build: the artifact carried AVX-512 (385 zmm references, 151
# AVX-512-only mnemonics) because the COPR builder has it, and on the target
# machine -- a 12th-gen i9 with AVX-512 fused off -- every run died with
# "Illegal instruction (core dumped)" while the same source built locally ran
# fine. So the target is pinned explicitly. x86-64-v2 is the level Fedora itself
# builds for, and the shader work is on the GPU, so a wider baseline buys nothing.
# Raise it to x86-64-v3 only if every machine that runs this is known to have
# AVX2.
%global zigcpu x86-64-v2

%build
# Zig's dependency fetch and compilation cache live under the builddir so nothing
# is written outside the build root. The dependency itself (zig-toml) comes over
# the network — see the enable_net note in the header.
export PATH="%{_builddir}/zig-x86_64-linux-%{zigversion}:$PATH"
export ZIG_GLOBAL_CACHE_DIR="%{_builddir}/zig-global-cache"
export ZIG_LOCAL_CACHE_DIR="%{_builddir}/zig-local-cache"
zig version
zig build --release=safe --build-id=sha1 -Dcpu=%{zigcpu} --summary all

%check
# Upstream's unit tests: parsers, the coordinate transform, config and file
# helpers, the window strip and its animation replay, the particle physics, the
# laser tracer, the effect clocks, the sprite player. They touch no compositor,
# so they run in a build chroot — a release that fails them does not publish.
export PATH="%{_builddir}/zig-x86_64-linux-%{zigversion}:$PATH"
export ZIG_GLOBAL_CACHE_DIR="%{_builddir}/zig-global-cache"
export ZIG_LOCAL_CACHE_DIR="%{_builddir}/zig-local-cache"
zig build test -Dcpu=%{zigcpu} --summary all

%install
# build.zig lays the whole tree out itself: bin/hyprglaze, share/hyprglaze/
# (24 shaders + the buddy sprite, the path the daemon falls back to when its
# data is not in the CWD) and lib/systemd/user/hyprglaze{,@}.service. The
# compile itself is a cache hit from %build.
export PATH="%{_builddir}/zig-x86_64-linux-%{zigversion}:$PATH"
export ZIG_GLOBAL_CACHE_DIR="%{_builddir}/zig-global-cache"
export ZIG_LOCAL_CACHE_DIR="%{_builddir}/zig-local-cache"
zig build --release=safe --build-id=sha1 -Dcpu=%{zigcpu} --prefix %{buildroot}%{_prefix}

%files
%license LICENSE
%doc README.md docs
%{_bindir}/hyprglaze
%{_datadir}/hyprglaze
%{_userunitdir}/hyprglaze.service
%{_userunitdir}/hyprglaze@.service

%changelog
* Tue Nov 17 2026 wegweg7979 <diode-crumble-0h@icloud.com> - 0.1.0-2.20261110gitfdafdcf
- Pin the CPU baseline to x86-64-v2. Zig defaults to -Dcpu=native, so the first
  build compiled for the COPR builder's AVX-512 and died with SIGILL on the
  target machines.

* Tue Nov 17 2026 wegweg7979 <diode-crumble-0h@icloud.com> - 0.1.0-1.20261110gitfdafdcf
- First Fedora packaging: the daemon, its 24 shaders and buddy sprite under
  /usr/share/hyprglaze, and the two systemd user units. Zig 0.17.1 is a pinned
  build-time source because Fedora 45 ships 0.16.0.
