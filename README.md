# err-trivia

A trivia plugin for [Errbot](http://errbot.io/). Features include:
  - Statistics
  - Hints
  - User aliases for calculating statistics
  - Randomized questions

Example game:
```
<aiden> !trivia start 1
<trivbot> What is the capital of Canada?
<trivbot> Hint: O--a--
<trivbot> Hint: Ot-a-a
<aiden> ottawa
trivbot> Correct!
<trivbot> Game finished! Stats: aiden: 1 point(s)
```

TODO:
  - Scrambled word questions
  - Script for importing questions (probably from a CSV) into the SQLite database
  - Fix suspect multi-threading with SQLite connection
  - Tests

## Installation

```
!repos install https://github.com/aidenhaak/err-trivia.git
```

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

## Recommend Configuration

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