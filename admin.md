# Admin install commands

Ubuntu 26.04 package names. Run the blocks of a section in order.

## perf2html scripts

`perf2html.sh`, `perf2html_diff.sh` and `perf2html_batch.sh` need these.

```sh
sudo apt-get install -y build-essential binutils ccache cmake cmark-gfm \
  coreutils curl dpkg linux-perf ninja-build nodejs npm python3 tar \
  util-linux valgrind xz-utils
sudo npm install -g speedscope
```

## Developers running test_all.sh

`scripts/test_all.sh` needs the perf2html scripts section above and these.

```sh
sudo apt-get install -y clang-format python3-pil python3-pip shfmt
sudo npm install -g prettier pyright
pip3 install --user --break-system-packages ruff
npx --yes @puppeteer/browsers install chrome@157.0.8103.78 \
  --path ~/.local/share/chrome-for-testing
```

The screenshot browser's libraries, after the browser install above:

```sh
sudo apt-get satisfy -y "$(paste -sd, \
  ~/.local/share/chrome-for-testing/chrome/linux-157.0.8103.78/chrome-linux64/deb.deps)"
```
