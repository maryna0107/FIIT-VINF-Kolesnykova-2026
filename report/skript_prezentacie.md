# Skript prezentácie – 1. časť projektu

Trvanie: ~10 minút. Text v úvodzovkách hovoríš, **[UKÁŽ: …]** je pokyn, čo otvoriť na obrazovke.

---

## Príprava (pred prezentáciou)

1. Otvor VS Code s projektom a terminál v priečinku projektu.
2. Raz si spusti, nech vieš, čo uvidíš:
   ```bash
   python3 -m unittest discover tests -v
   python3 -m indexer.search "easy dessert" --idf classic --limit 5
   python3 -m indexer.search "easy dessert" --idf bm25 --limit 5
   python3 -m indexer.search "dinner" --max-minutes 30 --max-calories 500 --limit 5
   ```
3. Otvor si v prehliadači svoju wiki stránku.

---

## 0. Úvod (~30 s)

„Môj projekt je vyhľadávač receptov. Recepty získavam z Food.com a v druhej časti ich obohatím o informácie z Wikipédie – napríklad aby systém vedel, že citrón, limetka a pomaranč sú citrusy, alebo aby k receptu na lasagne pridal jeho históriu.

V prvej časti mám hotový crawler, regex extraktor, vlastný index s dvoma metódami IDF, štatistiky a obe bonusové úlohy.“

---

## 1. Dáta (~1 min)

**[UKÁŽ: `metadata/downloads.tsv`]**

„Stiahla som **2 592 stránok receptov, spolu približne 840 megabajtov** HTML, teda viac ako požadovaných 500 MB.

Food.com má zoznam všetkých receptov podľa abecedy – kategórie 123 a A až Z. Aby boli dáta **vyvážené**, nebrala som tisíce receptov z jedného písmena, ale **z každej z 27 kategórií presne 100 URL**, spolu **2 700 URL**.

Každý pokus o stiahnutie je zapísaný tu, v `downloads.tsv` – má presne 2 700 riadkov. Pre každý pokus si ukladám ID receptu, URL, kam sa súbor uložil, HTTP status a veľkosť v bajtoch. **2 592 bolo úspešných, 108 vrátilo 404** – recept už na Food.com neexistuje. Takúto stránku neukladám, ale pokus zostane zapísaný.

Crawler sa predstaví ako študentský bot, čaká 10 sekúnd na odpoveď, medzi požiadavkami dáva 1 sekundu pauzu a nikdy neposiela viac požiadaviek naraz. Pri dočasnej chybe servera to skúsi ešte dvakrát. Celé sťahovanie trvalo asi hodinu a 20 minút.“

---

## 2. Ako dáta prechádzajú systémom (~3 min)

**[UKÁŽ: diagram `architecture.png` na wiki]**

„Ukážem to na jednom konkrétnom recepte – **Za'atar and Feta Corn Tostadas**.“

### Krok 1 – Discovery

„Crawler otvorí zoznam receptov na písmeno Z. Z HTML vytiahne odkazy na recepty pomocou **regulárneho výrazu** – to je vzor na hľadanie v texte. Hľadám odkazy v tvare `/recipe/názov-číslo`. Nájdenú URL zapíšem do `recipe_urls.tsv` spolu s kategóriou Z.“

### Krok 2 – Download

„Potom stránku stiahnem a uložím presne tak, ako prišla zo servera, do súboru `data/html/462404.html`. Súbor sa volá podľa **ID receptu** – to číslo na konci URL –, pretože je jedinečné a prepája všetky moje súbory. Do `downloads.tsv` pribudne riadok so statusom 200 a veľkosťou 274 kilobajtov.“

### Krok 3 – Extrakcia

**[UKÁŽ: sekcia 9 na wiki – kód extraktora]**

„Stránka má 274 kilobajtov, ale samotný recept je v nej skrytý v jednom bloku – `script type application/ld+json`. To je **schema.org**, verejný štandard pre recepty, ktorý používajú weby po celom svete. Preto extraktor nezávisí od vzhľadu stránky ani od CSS tried a nepoužívam XPath.

Z tohto bloku vyťahujem **regexmi** názov, ingrediencie, postup, časy, kategóriu, hodnotenie a kalórie. Výsledok ukladám do `recipes.jsonl` – jeden recept na jeden riadok.

Z ingrediencií robím **entity**: regexy odstránia množstvo, jednotku a poznámku. Z ‚1/4 cup feta‘ zostane iba ‚feta‘. Tieto entity budem v druhej časti spájať s Wikipédiou.“

### Krok 4 – Tokenizácia

„Text receptu potom rozdelím na slová – **tokeny**. Všetko dám na malé písmená a vyhodím slová ako *the*, *and*, *of*, ktoré nič neznamenajú. Rovnako spracujem aj dopyt používateľa, aby sa slová vždy zhodovali.“

### Krok 5 – Index

„Z tokenov vytvorím **invertovaný index**. To je slovník: pre každé slovo si zapamätám, v ktorých receptoch je a koľkokrát – to je **TF, term frequency**. Napríklad slovo *feta* je v 22 receptoch a v našom recepte 4-krát.

Index vytváram **raz**, po extrakcii, a uložím ho do `index.json`. Pri vyhľadávaní ho iba načítam. Výhoda: pri hľadaní slova feta nemusím prechádzať všetkých 2 591 receptov, hneď viem, ktorých 22 ho obsahuje.

Každý krok číta súbor od predchádzajúceho kroku a zapisuje vlastný. Databázu nepoužívam – zadanie ju zakazuje. A keď opravím extraktor, spustím iba ten a nemusím nič sťahovať znova.“

---

## 3. Metódy IDF (~2 min)

**[UKÁŽ: sekcia 11 na wiki – tabuľka so vzorcami]**

„Keď niekto vyhľadáva, pre každý recept spočítam skóre: **TF krát IDF**, sčítané cez všetky slová dopytu.

**TF** hovorí, koľkokrát je slovo v recepte. **IDF** hovorí, aké je slovo vzácne. Vzácne slová sú dôležité – keď niekto napíše *feta*, je to veľmi konkrétne. Bežné slová ako *easy* alebo *salt* sú skoro v každom recepte, takže o recepte veľa nepovedia.

Implementovala som dve metódy:

**Klasické IDF** je logaritmus N lomeno df – N je počet všetkých receptov, df je počet receptov so slovom.

**BM25 IDF** je logaritmus zlomku: v čitateli je N mínus df plus 0,5, teda v koľkých receptoch slovo **nie je**, v menovateli df plus 0,5, teda v koľkých receptoch slovo **je**. Tá 0,5 iba zabráni deleniu nulou.

Pri vzácnych slovách sú takmer rovnaké – *feta* má 2,07 a 2,06. Líšia sa pri bežných slovách. Slovo *easy* je v 58 % receptov. Klasické IDF mu dá malú **kladnú** váhu, plus 0,24. BM25 mu dá **zápornú** váhu, mínus 0,14 – lebo slovo je častejšie v receptoch ako mimo nich, takže ho považuje za šum.

Prečo práve tieto dve: klasické je základná verzia z učebníc a BM25 sa od nej **najviac líši**, takže porovnanie má o čom hovoriť. Zvažovala som aj vyhladené IDF, ale to sa od klasického líši len posunom a nikdy nie je záporné. A BM25 používa aj Lucene, takže v druhej časti budem môcť svoj index s Lucene porovnať.

Obe metódy aj celý index sú môj vlastný kód v Pythone, žiadnu knižnicu na vyhľadávanie nepoužívam.“

---

## 4. Porovnanie (~2 min)

**[UKÁŽ: sekcia 12 na wiki]**

„Metódy som porovnala na šiestich dopytoch. Pri dvoch so vzácnymi slovami – *chocolate cake* a *garlic spinach* – je poradie rovnaké alebo takmer rovnaké. Pri štyroch s bežnými slovami sa líši.

Najlepší príklad je **easy dessert**.“

**[UKÁŽ naživo:]**
```bash
python3 -m indexer.search "easy dessert" --idf classic --limit 5
python3 -m indexer.search "easy dessert" --idf bm25 --limit 5
```

„Klasické IDF dá na prvé miesto *J-E-L-L-O Fruit and Cookie Dream* – recept, ktorý o sebe trikrát píše, že je *easy*. BM25 slovo *easy* potrestá, ten recept vypadne z top 5 a vyhrá *C.M.P. Dessert*, kde je *dessert* štyrikrát.

Najväčší rozdiel je pri *quick easy dinner* – zhoda prvých desiatich výsledkov je iba 6 z 10.

**Ktorá metóda je lepšia?** Žiadna vždy. BM25 je lepšie, keď je bežné slovo iba výplň – pri *salt pepper chicken* soľ nič nehovorí, človek chce kurča. Klasické je lepšie, keď to používateľ myslí vážne – pri *easy dessert* naozaj chce jednoduchý dezert. Objektívne to vyhodnotím cez precision a recall v druhej časti.“

---

## 5. Štatistiky (~1 min)

**[UKÁŽ: sekcia 13 na wiki]**

„Zo stiahnutých stránok mám **2 591 unikátnych receptov**, spolu **24 473 riadkov ingrediencií** a **4 048 rôznych entít ingrediencií**. Index má **12 158 rôznych slov**.

Pri spracovaní som našla dve zaujímavé veci. Prvá – **duplicitu obsahu**: dve rôzne URL viedli na ten istý recept, lebo Food.com jednu presmerúva na druhú. Bežná kontrola URL to nezachytí, ale ja ju odhalím podľa canonical URL v stránke.

Druhá – **823 receptov, takmer tretina, nemalo vlastný popis**. Food.com im automaticky doplnil vetu ‚Make and share this … recipe from Food.com‘. Tá pridávala do indexu šum – slová ako *share*, *recipe*, *food* –, tak ju regexom odstraňujem.“

**[voliteľne UKÁŽ filter:]**
```bash
python3 -m indexer.search "dinner" --max-minutes 30 --max-calories 500 --limit 5
```

„Extrahovaný čas a kalórie viem použiť aj ako filter – toto je otázka z môjho návrhu: večera do 30 minút a pod 500 kalórií.“

---

## 6. Bonusové úlohy (~1 min)

**[UKÁŽ naživo:]**
```bash
python3 -m unittest discover tests -v
```

„Prvý bonus sú **unit testy regexov**. Mám **30 testov** a každý patrí k jednému regulárnemu výrazu. Regex na URL z crawlera testujem na **20 listing stránkach** – na každej musí nájsť presne 100 odkazov na recepty. Regexy extraktora testujem na **20 stránkach receptov** – napríklad že na každej nájde názov, ingrediencie a kroky, a pri známych receptoch kontrolujem presné hodnoty. Stránky mám uložené pri testoch, takže testy nepotrebujú internet. Všetky prechádzajú.

Druhý bonus je **počet tokenov cez tiktoken** – to je knižnica od OpenAI, ktorá počíta tokeny tak, ako text čítajú jazykové modely. Surové HTML má **360 miliónov tokenov**, samotné recepty iba **0,7 milióna** – teda dve desatiny percenta. To ukazuje, prečo je extrakcia dôležitá: väčšina stránky sú skripty, menu a reklamy.“

---

## 7. Záver (~20 s)

„V druhej časti stiahnem dump Wikipédie, v Sparku z neho vytiahnem názvy, presmerovania a kategórie, spojím ich s mojimi entitami ingrediencií a kuchýň a vytvorím index v Lucene, ktorý porovnám s mojím vlastným. Ďakujem.“

---

## Ťahák na otázky

| Otázka | Odpoveď |
|---|---|
| Prečo `requests`, nie Scrapy? | Jeden web, známa štruktúra URL, sekvenčne – framework netreba, vlastný kód viem presne vysvetliť. |
| Prečo 10 s a 1 s? | 10 s dá pomalému serveru čas, ale jedna zaseknutá požiadavka nezablokuje beh. 1 s = najviac ~1 požiadavka za sekundu, ohľad na server. |
| Ako viete, kde končí stránkovanie? | Food.com za poslednou stránkou opakuje poslednú stránku – kategóriu ukončím, keď nepríde žiadna nová URL. |
| Prečo nie všetky recepty? | Celé písmená majú tisíce receptov, A–Z by trvalo dni. Zvolila som vyvážený výber; crawler vie aj všetko (`MAX_PAGES_PER_CATEGORY = None`). |
| Mazali ste niečo? | Nie. Prvý, nevyvážený beh je archivovaný, metadáta sa iba dopĺňajú. |
| Nie je schema.org extrakcia podľa štruktúry stránky? | Nie, je to verejný štandard pre recepty na celom webe, nie rozloženie Food.com. Žiadne XPath ani CSS triedy. |
| Koľkokrát vytvárate index? | Raz po extrakcii. IDF sa neukladá, počíta sa pri dopyte, takže jeden index slúži obom metódam. |
| Použili ste Lucene? | Nie. BM25 je vzorec, ktorý som implementovala sama. Lucene príde v 2. časti na porovnanie. |
| Slabé miesta? | TF je surový počet, takže dlhé recepty majú výhodu (riešenie: logaritmické TF alebo delenie dĺžkou ako plné BM25). Bez lematizácie sú *egg* a *eggs* dve entity. Tokenizer rozdelí *za'atar* na *za* a *atar*. Precision a recall zatiaľ nemám. |
| Prečo 837 vs. 878 MB? | To isté množstvo – 837,5 MB v jednotkách po 1 024, 878 MB v jednotkách po 1 000. |
