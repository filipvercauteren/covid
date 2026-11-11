# How the unemployment rise is calculated

*Jobs criterion — column `unemployment_rise_pp` in table `society_covid`,
calculated by `social_changes()` in `build_resilience_db.py`.*

The calculation is a chain of five pandas operations. Each one works on **all countries at once**,
with no loop per country. Below it is run on real data for three countries, plus one aggregate,
to show what happens at each step.

## Step 0: the input, a "long" table

`social` holds one row per country per year (World Bank indicator `SL.UEM.TOTL.ZS`,
modelled ILO estimate):

```
iso_code  year  unemployment_pct  is_aggregate
     BEL  2019              5.36             0
     BEL  2020              5.54             0
     BEL  2021              6.25             0
     ...
     EUU  2019              6.68             1   ← European Union: an aggregate
     ...
     USA  2020              8.06             0
```

## Step 1: filter out aggregates

```python
countries = social[social["is_aggregate"] == 0]
```

`social["is_aggregate"] == 0` produces a column of `True`/`False`. The square brackets keep only
the rows marked `True`. **EUU (the European Union) is dropped**, leaving BEL, ITA and USA.

## Step 2: pivot from long to wide

```python
wide = countries.pivot_table(index="iso_code", columns="year", values=[...])
unemployment = wide["unemployment_pct"]
```

`pivot_table` reshapes the table so each country becomes **one row** and each year becomes
**a column**:

```
year       2018  2019  2020  2021  2022  2023
iso_code
BEL        5.94  5.36  5.54  6.25  5.57  5.55
ITA       10.54  9.88  9.19  9.50  8.07  7.63
USA        3.90  3.67  8.06  5.35  3.65  3.64
```

This is the key step: you can now compare years with each other **within a row**.

## Step 3: select the COVID years

```python
unemployment[years]      # years = [2020, 2021, 2022]
```

```
year      2020  2021  2022
BEL       5.54  6.25  5.57
ITA       9.19  9.50  8.07
USA       8.06  5.35  3.65
```

## Step 4: highest value per row

```python
unemployment[years].max(axis=1)
```

`axis=1` means **horizontally, across the columns**: the maximum is taken per country, over its
three years. (`axis=0` would give the maximum per year across all countries.)

```
BEL    6.25    ← 2021
ITA    9.50    ← 2021
USA    8.06    ← 2020
```

## Step 5: take the 2019 column

```python
unemployment[BASELINE_YEAR]      # BASELINE_YEAR = 2019
```

```
BEL    5.36
ITA    9.88
USA    3.67
```

## Step 6: subtract, row by row

```python
unemployment[years].max(axis=1) - unemployment[BASELINE_YEAR]
```

Pandas lines up the two columns **by country code** (the index), so it always subtracts BEL from
BEL, ITA from ITA, and so on:

```
         max     2019     result
BEL     6.25  −  5.36  =   0.88
ITA     9.50  −  9.88  =  −0.39   ← fell!
USA     8.06  −  3.67  =   4.39
```

That's `unemployment_rise_pp`.

## What the result shows

- **Belgium, +0.88:** a small rise. Temporary unemployment kept people formally employed.
- **USA, +4.39:** a big jump in 2020, because people were simply laid off. It fell back quickly
  afterwards.
- **Italy, −0.39:** even the *highest* value of 2020–22 is below 2019. Unemployment fell because
  many people stopped looking for work, so they no longer counted as unemployed. A negative value
  here doesn't mean Italy's job market did well.

**"All at once"** means the real script doesn't run this for 3 countries but for about 190
simultaneously. `.max(axis=1)` and the subtraction work on whole columns, each in a single
operation, with no `for` loop. That's how pandas normally works: you describe the operation per
column, and pandas applies it to every row.
