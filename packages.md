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
sudo apt-get install -y clang-format python3-pil python3-pip shfmt
pip3 install --user --break-system-packages pyright ruff
npm install -g --prefix ~/.npm-global prettier
npx --yes @puppeteer/browsers install chrome@157.0.8103.78 \
  --path ~/.local/share/chrome-for-testing
```

The screenshot browser's libraries, after the browser install above:

```sh
sudo apt-get satisfy -y "$(paste -sd, \
  ~/.local/share/chrome-for-testing/chrome/linux-157.0.8103.78/chrome-linux64/deb.deps)"
```
