# The World in One Day — 19 November 2026

[![news-image-20261119](https://make.fun/badge/news-image-20261119.svg)](https://make.fun/bounty/news-image-20261119)
[![rank](https://make.fun/badge/news-image-20261119/Xyzvixx/news-image-20261119/rank.svg)](https://make.fun/bounty/news-image-20261119)
[![reward](https://make.fun/badge/news-image-20261119/Xyzvixx/news-image-20261119/reward.svg)](https://make.fun/bounty/news-image-20261119)

One image that sums up the world's news of **Thursday, 19 November 2026**,
drawn as a newspaper front page. `main.py` (Python 3.13, standard library
only, no network) copies `entry.png` to `/output/entry.png`, verifying first
that it is a whole PNG within the limits (1024×1024, under 1 MiB). Two runs
write byte-identical output.

![The World in One Day — 19 November 2026](entry.png)

## The day's news in the image

| Story | What the image says |
|---|---|
| Trump, Xi and Putin set to meet in Shenzhen | First three-way meeting set for Nov. 19; nuclear arms and the Iran war on the agenda |
| US and Iran trade fire again | U.S. struck Qeshm Island Nov. 17; Iran hit U.S. sites in Bahrain and Kuwait Nov. 18 |
| House Democrats nominate Jeffries | Won 251–11, Nov. 18; first Black speaker if elected Jan. 3 |
| Grand Theft Auto VI arrives | Global rollout begins after a 13-year wait |
| Van Gogh sells for $190.4m | 'Blossoming Chestnut Trees' sets artist record; reported Nov. 19 |
| World court set to rule in Rohingya case | The Gambia's genocide case against Myanmar; due 08:00 GMT |
| Also today | Cyclone Akvan due off India's coast ~Nov. 20; BBC: Anthropic could be valued at $1.4tn or more if it goes public; Israeli tanks cross Gaza ceasefire line; EU proposes €45bn Ukraine loan, repaid from Russian reparations |

Headlines were checked against wire reports published on 18–19 November
2026 (Reuters, AP, BBC and other wire reports). Prior-day events carry
their Nov. 18 date on the page. The pictures are flat editorial
illustrations made for this entry — not photographs of the events — as the
footer of the image itself says.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png (462,656 bytes, 1024x1024)
```

## License

MIT — see [LICENSE](LICENSE).
