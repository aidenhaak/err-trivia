# err-trivia

A trivia plugin for [Errbot](http://errbot.io/). Features include:
  - Statistics
  - Hints
  - User aliases for calculating statistics
  - Randomized questions

Example game:
```
<aiden> !trivia start 2
<trivbot> What is the capital of Canada?
<trivbot> Hint: O--a--
<trivbot> Hint: Ot-a-a
<aiden> ottawa
<trivbot> Correct!
<trivbot> Unscramble this word: l n b c e m a u a
<trivbot> Hint: --b-l-n--
<trivbot> Hint: -mb-l-nc-
<trivbot> Hint: amb-l-nce
<trivbot> Answer: ambulance
<trivbot> Game finished! Stats: aiden: 1 point(s)
```

TODO:
  - Fix suspect multi-threading with SQLite connection
  - Tests

## Installation

```
!repos install https://github.com/aidenhaak/err-trivia.git
```

## Creating a Database File

Run the import script in the util folder:

```shell
./util/import_questions.py -q questions.csv -w words.txt -o trivia.db
```

The CSV file should match the format of the `example_questions.csv` file. Each row should match the following pattern:

```
"Question?","Answer"
```

The words file should match the format of the `example_words.txt` file. Each line should have a separate line:

```
Word1
Word2
```

This script will either create a new SQLite database or import the questions and scrambled into an existing database.

## Available Commands

### Game

#### Start a Game

```
!trivia start [num_questions]
```
Starts a new trivia game in the current channel if one is not already running. If number of questions is not specified the default is 10.

#### Stop a Game

```
!trivia stop
```

Stops any in progress game in the current channel.

#### Skip a Question

```
!skip
```

Skips the current question if there is one.

### Statistics

#### Get a User's Statistics

```
!stats [Nick]
```

Gets the game statistics for the specified nick. If no nick is specified the nick that sent the command is used instead.

#### Hall of Fame

```
!hof
```

Get the statistics for the top 10 trivia players.

### Aliases

Aliases are used to combine points for different users when calculating the game statistics.

#### Add a User Alias

```
!trivia alias add OriginalNick AliasNick
```

Adds a new alias for the `OriginalNick`. Nesting of aliases is not supported and only the first alias is used for calculating the game statistics - i.e. aliases of aliases are not included for game statistics.

#### Remove a User Alias

```
!trivia alias remove OriginalNick AliasNick
```

Removes an alias if it exists.

#### List a User's Aliases

```
!trivia alias list OriginalNick
```

Lists any aliases for the specified nick.

## Configuration

You can configure the trivia plugin by sending the bot the following command:

```
!plugin config Trivia { 'HINT_DELAY_SECONDS': 5, 'QUESTION_DELAY_SECONDS': 5, 'DATABASE_PATH': './trivia.db' }
```

### Limiting Access

It's probably a good idea to limit everything except the `!stats` and `!hof` commands to bot admins. This can be done by adding the following to your `config.py` file:

```python
ACCESS_CONTROLS = {
    "Trivia:start": {
        "allowusers": BOT_ADMINS,
        "allowmuc": True
    },
    "Trivia:stop": {
        "allowusers": BOT_ADMINS,
        "allowmuc": True
    },
    "Trivia:skip": {
        "allowusers": BOT_ADMINS,
        "allowmuc": True
    }
}
```
