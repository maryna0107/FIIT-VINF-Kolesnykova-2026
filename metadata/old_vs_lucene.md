# Porovnanie: starý index vs. Lucene

Recepty: 2591 (starý), 2591 (Lucene). Top 5 výsledkov, zhoda = koľko z top 10 je v oboch.

## `chocolate cake` – bežný dopyt (OR)

Lucene dopyt: `+(((name:chocol)^3.0 (ingredient:chocol)^2.0 (category:chocol)^1.5 (keywords:chocol)^1.5 (wiki_dish:chocol)^1.0 (cuisine:chocol)^1.0 (description:chocol)^1.0 (instructions:chocol)^0.5) ((name:cake)^3.0 (ingredient:cake)^2.0 (category:cake)^1.5 (keywords:cake)^1.5 (wiki_dish:cake)^1.0 (cuisine:cake)^1.0 (description:cake)^1.0 (instructions:cake)^0.5))`

Nájdené: starý 410, Lucene 530. Zhoda top 10: 4/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | *the Real* Black Tie Mousse Cake by Olive Garden | Ugly Chocolate Cake |
| 2 | V's Chocolate Coma Cake (Triple Layer) | $100 Chocolate Cake |
| 3 | C T's Ice Cream Cake -- Much Like D Q | Waffle Chocolate Cake |
| 4 | La Bete Noire Chocolate Flourless Cake | B. B. King's German Chocolate Cake |
| 5 | "We Thought It was a Layer Cake Sandwich" | Wacky Chocolate Cake |

## `easy chicken dinner` – časté slová

Lucene dopyt: `+(((name:easi)^3.0 (ingredient:easi)^2.0 (category:easi)^1.5 (keywords:easi)^1.5 (wiki_dish:easi)^1.0 (cuisine:easi)^1.0 (description:easi)^1.0 (instructions:easi)^0.5) ((name:chicken)^3.0 (ingredient:chicken)^2.0 (category:chicken)^1.5 (keywords:chicken)^1.5 (wiki_dish:chicken)^1.0 (cuisine:chicken)^1.0 (description:chicken)^1.0 (instructions:chicken)^0.5) ((name:dinner)^3.0 (ingredient:dinner)^2.0 (category:dinner)^1.5 (keywords:dinner)^1.5 (wiki_dish:dinner)^1.0 (cuisine:dinner)^1.0 (description:dinner)^1.0 (instructions:dinner)^0.5))`

Nájdené: starý 1722, Lucene 1750. Zhoda top 10: 2/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | J-Slo's Sesame Chicken | Uber-Easy Chicken |
| 2 | O'charley's Chicken Harvest Soup | X-Traordinarily Easy Chicken Curry |
| 3 | Ugly Naked Chicken | 1 Pot Dinner |
| 4 | G.a.b.'s Chicken Puff Pie (Aka Chicken Pot Pie) | Fabulous and Easy Dinner Rolls |
| 5 | "Smells Like Sunday" Chicken Fricassee With Meatballs | Habanero Grilled Chicken on a Bed of Pasta |

## `chicken AND garlic NOT onion` – Boolean AND, NOT

Lucene dopyt: `+(+((name:chicken)^3.0 (ingredient:chicken)^2.0 (category:chicken)^1.5 (keywords:chicken)^1.5 (wiki_dish:chicken)^1.0 (cuisine:chicken)^1.0 (description:chicken)^1.0 (instructions:chicken)^0.5) +((name:garlic)^3.0 (ingredient:garlic)^2.0 (category:garlic)^1.5 (keywords:garlic)^1.5 (wiki_dish:garlic)^1.0 (cuisine:garlic)^1.0 (description:garlic)^1.0 (instructions:garlic)^0.5) -((name:onion)^3.0 (ingredient:onion)^2.0 (category:onion)^1.5 (keywords:onion)^1.5 (wiki_dish:onion)^1.0 (cuisine:onion)^1.0 (description:onion)^1.0 (instructions:onion)^0.5))`

Nájdené: starý 101, Lucene 82. Zhoda top 10: 4/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | Oak Town Garlic Vinegar Chicken | W1N3 Honey Garlic Chicken Thighs |
| 2 | J-Slo's Sesame Chicken | D'Arabian's Roasted Garlic Clove Chicken Thighs |
| 3 | -- Chicken Cheddar Crepes With Mushrooms -- | Jack Daniel's Glazed Chicken Breast Stuffed With Garlic and Herb |
| 4 | D'Arabian's Roasted Garlic Clove Chicken Thighs | L'aido Boulido (French Garlic Soup) |
| 5 | Ugly Naked Chicken | G-l-m Chicken |

## `(cake OR pie) AND apple` – Boolean OR, zátvorky

Lucene dopyt: `+(+(((name:cake)^3.0 (ingredient:cake)^2.0 (category:cake)^1.5 (keywords:cake)^1.5 (wiki_dish:cake)^1.0 (cuisine:cake)^1.0 (description:cake)^1.0 (instructions:cake)^0.5) ((name:pie)^3.0 (ingredient:pie)^2.0 (category:pie)^1.5 (keywords:pie)^1.5 (wiki_dish:pie)^1.0 (cuisine:pie)^1.0 (description:pie)^1.0 (instructions:pie)^0.5)) +((name:appl)^3.0 (ingredient:appl)^2.0 (category:appl)^1.5 (keywords:appl)^1.5 (wiki_dish:appl)^1.0 (cuisine:appl)^1.0 (description:appl)^1.0 (instructions:appl)^0.5))`

Nájdené: starý 14, Lucene 44. Zhoda top 10: 7/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | A & P Spanish Bar Cake | Fabulous Apple Pie Cake |
| 2 | $25,000 Apple Pie | $25,000 Apple Pie |
| 3 | Gâteau De Pommes Grand-Mère (Grandmother's Apple Ca | B. C. Apple Cake |
| 4 | Gâteau Rustique (Apple Cinnamon Cake) | Gâteau Rustique (Apple Cinnamon Cake) |
| 5 | B. C. Apple Cake | A & P Spanish Bar Cake |

## `"olive oil"` – fráza

Lucene dopyt: `+((name:"oliv oil")^3.0 (ingredient:"oliv oil")^2.0 (category:"oliv oil")^1.5 (keywords:"oliv oil")^1.5 (wiki_dish:"oliv oil")^1.0 (cuisine:"oliv oil")^1.0 (description:"oliv oil")^1.0 (instructions:"oliv oil")^0.5)`

Nájdené: starý 914, Lucene 344. Zhoda top 10: 1/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | ' Utah ' Scones (Deep-Fried) | F&t Extra-Garlicky Bruschetta |
| 2 | Yai-Yai's Moussaka | Rabbit Stifado |
| 3 | Za'atar-Crusted Tuna With Cured Tomatoes and Merguez Vinaigrette | P. P. (Pesto Panini) |
| 4 | Yalantzi Dolmathes | D.A.M. Bruschetta Caprese |
| 5 | B's Cinnamon Sugar Italian Doughnut | ' Boiled Water ' Garlic Soup |

## `tomatoes` – stemming (tomatoes = tomato)

Lucene dopyt: `+((name:tomato)^3.0 (ingredient:tomato)^2.0 (category:tomato)^1.5 (keywords:tomato)^1.5 (wiki_dish:tomato)^1.0 (cuisine:tomato)^1.0 (description:tomato)^1.0 (instructions:tomato)^0.5)`

Nájdené: starý 339, Lucene 511. Zhoda top 10: 3/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | Méli-Mélo:a Muddle and Medley of Heirloom Tomatoes | D's Herbed Tomato Soup |
| 2 | Yalanchi Stuffed Tomatoes | "Tomato |
| 3 | Za'atar Marinated Tomato Salad | Za'atar Tomatoes |
| 4 | Za'atar-Crusted Tuna With Cured Tomatoes and Merguez Vinaigrette | Habiba (chicken & Tomatoes) |
| 5 | I Only Changed a Couple Things Green Stuffed Baked Tomatoes | 'tomokra' (Stewed Tomatoes and Okra) |

## `spagetti~` – fuzzy (preklep)

Lucene dopyt: `+((name:spagetti~2)^3.0 (ingredient:spagetti~2)^2.0 (category:spagetti~2)^1.5 (keywords:spagetti~2)^1.5 (wiki_dish:spagetti~2)^1.0 (cuisine:spagetti~2)^1.0 (description:spagetti~2)^1.0 (instructions:spagetti~2)^0.5)`

Nájdené: starý 1, Lucene 45. Zhoda top 10: 0/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | Quad-Cheese Ziti | A & R Bar-Be-Que Spaghetti |
| 2 |  | L.A. Times Spaghetti |
| 3 |  | D's Chinese Spaghetti |
| 4 |  | *spaghetti Squares* |
| 5 |  | V-8 Spaghetti |

## `choco*` – wildcard

Lucene dopyt: `+((name:choco*)^3.0 (ingredient:choco*)^2.0 (category:choco*)^1.5 (keywords:choco*)^1.5 (wiki_dish:choco*)^1.0 (cuisine:choco*)^1.0 (description:choco*)^1.0 (instructions:choco*)^0.5)`

Nájdené: starý 0, Lucene 352. Zhoda top 10: 0/10

| # | starý index | Lucene |
|---:|---|---|
| 1 |  | Habanero and Orange Chocolate Chip Cookies |
| 2 |  | #1 Chocolate Chip Cookies |
| 3 |  | Earl Grey Hot Chocolate |
| 4 |  | V's White Chocolate Cheesecake |
| 5 |  | "Chocolate |

## `flatbread` – Wikipédia: abstrakt jedla

Lucene dopyt: `+((name:flatbread)^3.0 (ingredient:flatbread)^2.0 (category:flatbread)^1.5 (keywords:flatbread)^1.5 (wiki_dish:flatbread)^1.0 (cuisine:flatbread)^1.0 (description:flatbread)^1.0 (instructions:flatbread)^0.5)`

Nájdené: starý 7, Lucene 37. Zhoda top 10: 5/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | Naan (Indian Flatbread) | Naan (Indian Flatbread) |
| 2 | Naan | Naan Style Flatbread |
| 3 | L'harsha | Naan Flatbread Pizza |
| 4 | Naan (No-Knead) | Naan (No-Knead) |
| 5 | Naan Style Flatbread | Naan |

## `cuisine:mexican` – Wikipédia: pole cuisine

Lucene dopyt: `+cuisine:mexican`

Nájdené: starý 151, Lucene 95. Zhoda top 10: 2/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | ! Arriba ! Baked Winter Squash Mexican-Style | "Sour Cream" Avocado Dip (vegan) |
| 2 | V's Mexican Lasagna | 'lil'john's Oven Deep Pit Rub |
| 3 | M-M-M- Good Mexican Rice | Ya Gotta Try This Salsa/Taco Dip |
| 4 | Raachie's Mexican Rice | Ca Kitchen White Corn Tortilla Soup |
| 5 | V's Simple Savory Mexican Quiche | ! Arriba ! Baked Winter Squash Mexican-Style |

## `cake NOT chocolate` – Boolean NOT

Lucene dopyt: `+(((name:cake)^3.0 (ingredient:cake)^2.0 (category:cake)^1.5 (keywords:cake)^1.5 (wiki_dish:cake)^1.0 (cuisine:cake)^1.0 (description:cake)^1.0 (instructions:cake)^0.5) -((name:chocol)^3.0 (ingredient:chocol)^2.0 (category:chocol)^1.5 (keywords:chocol)^1.5 (wiki_dish:chocol)^1.0 (cuisine:chocol)^1.0 (description:chocol)^1.0 (instructions:chocol)^0.5))`

Nájdené: starý 116, Lucene 180. Zhoda top 10: 5/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | "We Thought It was a Layer Cake Sandwich" | 'Legally Blonde' Elle Woods Cake |
| 2 | 1 Minute Mug Cake for One | C T's Ice Cream Cake -- Much Like D Q |
| 3 | 'Legally Blonde' Elle Woods Cake | Ugly Cake |
| 4 | A Better Burnt Almond Cake | Jack Daniel's Bundt Cake |
| 5 | Jack Daniel's Bundt Cake | 1 Minute Mug Cake for One |

## `chicken minutes:[* TO 30] calories:[* TO 500]` – range

Lucene dopyt: `+((name:chicken)^3.0 (ingredient:chicken)^2.0 (category:chicken)^1.5 (keywords:chicken)^1.5 (wiki_dish:chicken)^1.0 (cuisine:chicken)^1.0 (description:chicken)^1.0 (instructions:chicken)^0.5) #minutes:[-2147483648 TO 30] #calories:[-Infinity TO 500.0]`

Nájdené: starý 101, Lucene 119. Zhoda top 10: 5/10

| # | starý index | Lucene |
|---:|---|---|
| 1 | 's Style Chicken Salad | 's Style Chicken Salad |
| 2 | G-l-m Chicken | Habanero Grilled Chicken on a Bed of Pasta |
| 3 | OAMC Chicken Nuggets | G-l-m Chicken |
| 4 | Habanero Grilled Chicken on a Bed of Pasta | A Chicken Parmigiana |
| 5 | La Choy Chinese Chicken With Water Chestnuts | 'my Thai' Chicken Soup |
