# Štatistika dát

## Crawling

| Metrika | Hodnota |
|---|---:|
| Objavené URL receptov | 2700 |
| – z každej z 27 kategórií (`123`, `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, `I`, `J`, `K`, `L`, `M`, `N`, `O`, `P`, `Q`, `R`, `S`, `T`, `U`, `V`, `W`, `X`, `Y`, `Z`) | 100 |
| Vyskúšané URL (download) | 2700 |
| – HTTP 200 | 2592 |
| – HTTP 404 | 108 |

## Stiahnuté dokumenty

| Metrika | Hodnota |
|---|---:|
| Počet HTML dokumentov | 2592 |
| Veľkosť na disku | 837.5 MB |
| Priemerná veľkosť dokumentu | 331 KB |
| Najmenší / najväčší dokument | 222 KB / 657 KB |
| Duplicitné dokumenty (rovnaký recept pod inou URL) alebo bez receptu | 1 |
| Relevantné dokumenty (unikátny recept s ingredienciami) | 2591 (100.0 %) |

## Extrahované dáta

| Metrika | Hodnota |
|---|---:|
| Extrahované recepty | 2591 |
| Ingrediencie (riadky) | 24473 |
| Unikátne ingrediencie (entity) | 4048 |
| Unikátne kategórie | 175 |
| Veľkosť extrahovaného textu | 2.8 MB |

## Tokeny (tiktoken, `o200k_base`)

| Metrika | Hodnota |
|---|---:|
| Tokeny v raw HTML | 360 189 240 |
| Tokeny v extrahovanom texte | 696 808 |
| Priemer tokenov na recept (extrahovaný text) | 269 |
