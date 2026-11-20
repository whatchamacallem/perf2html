# Admin install commands

Ubuntu 26.04 package names. Run the blocks of a section in order.

## perf2html scripts

`perf2html.sh`, `perf2html_diff.sh` and `perf2html_batch.sh` need these.

```sh
sudo sed -i 's/^Types: deb$/Types: deb deb-src/' \
  /etc/apt/sources.list.d/ubuntu.sources
sudo apt-get update
sudo apt-get install -y build-essential binutils ccache cmake cmark-gfm \
  coreutils dpkg dpkg-dev libc6-dbg linux-perf ninja-build nodejs npm \
  python3 tar util-linux valgrind xz-utils
sudo npm install -g speedscope
```

## Developers running test_all.sh

`scripts/test_all.sh` needs the perf2html scripts section above and these. The
packages outside apt go in the home dir at the locations specified.

```sh
sudo apt-get install -y clang-format python3-pil python3-pip shfmt xvfb
pip3 install --user --break-system-packages pyright ruff
npm install -g --prefix ~/.npm-global prettier
npx --yes @puppeteer/browsers install chrome@157.0.8103.78 \
  --path ~/.local/share/chrome-for-testing
npx --yes @puppeteer/browsers install firefox@stable_160.0.1 \
  --path ~/.local/share/firefox-for-testing
mkdir -p ~/.local/share/seamonkey-for-testing/2.53.24
curl -L https://archive.seamonkey-project.org/releases/2.53.24/linux-x86_64/en-US/seamonkey-2.53.24.en-US.linux-x86_64.tar.bz2 \
  | tar -xj -C ~/.local/share/seamonkey-for-testing/2.53.24
sudo npx playwright install-deps 
PLAYWRIGHT_BROWSERS_PATH=~/.local/share/webkit-for-testing \
  npx --yes playwright@1.65.1 install webkit
```

Chrome's libraries, after the browser install above:

```sh
sudo apt-get satisfy -y "$(paste -sd, \
  ~/.local/share/chrome-for-testing/chrome/linux-157.0.8103.78/chrome-linux64/deb.deps)"
```

Firefox's libraries, the Depends line of Mozilla's own firefox 160.0.1
package as this release names them:

```sh
sudo apt-get install -y libasound2t64 libatk1.0-0t64 libc6 libcairo-gobject2 \
  libcairo2 libdbus-1-3 libfontconfig1 libfreetype6 libgcc-s1 \
  libgdk-pixbuf-2.0-0 libglib2.0-0t64 libgtk-3-0t64 libpango-1.0-0 \
  libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb-shm0 libxcb1 \
  libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 \
  libxrandr2 libxrender1
```

SeaMonkey's libraries, the system libraries its own binaries name, which
`readelf -d` lists:

```sh
sudo apt-get install -y libatk1.0-0t64 libc6 libcairo-gobject2 libcairo2 \
  libdbus-1-3 libdbus-glib-1-2 libfontconfig1 libfreetype6 libgcc-s1 \
  libgdk-pixbuf-2.0-0 libglib2.0-0t64 libgtk-3-0t64 libpango-1.0-0 \
  libpangocairo-1.0-0 libpangoft2-1.0-0 libstdc++6 libx11-6 libx11-xcb1 \
  libxcb-shm0 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 \
  libxfixes3 libxi6 libxrender1 libxt6t64
```

WebKit's libraries, the packages Playwright 1.65.1's own host check names for
the libraries its WebKit build lacks, no font package among them:

```sh
sudo apt-get install -y gstreamer1.0-libav libavif16 libenchant-2-2 \
  libevent-2.1-7t64 libgles2 libgraphene-1.0-0 libgstreamer-gl1.0-0 \
  libgstreamer-plugins-bad1.0-0 libgstreamer-plugins-base1.0-0 \
  libgstreamer1.0-0 libgtk-4-1 libharfbuzz-icu0 libhyphen0 libmanette-0.2-0 \
  libopus0 libsecret-1-0 libsoup-3.0-0 libwayland-server0
```
