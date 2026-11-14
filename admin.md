# Admin install commands

Ubuntu 26.04 package names. Run the blocks in order.

## System packages and global npm tools

```sh
sudo apt-get install -y build-essential binutils ccache cmake cmark-gfm \
  coreutils curl dpkg clang-format linux-perf ninja-build nodejs npm \
  python3 python3-pil python3-pip shfmt tar util-linux valgrind xz-utils
sudo npm install -g prettier pyright speedscope
```

## User tools

```sh
pip3 install --user --break-system-packages ruff
npx --yes @puppeteer/browsers install chrome@157.0.8103.78 \
  --path ~/.local/share/chrome-for-testing
```

## Screenshot browser libraries

```sh
sudo apt-get satisfy -y "$(paste -sd, \
  ~/.local/share/chrome-for-testing/chrome/linux-157.0.8103.78/chrome-linux64/deb.deps)"
```
