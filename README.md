# ShowOrderer
## Introduction
This is a program designed to help the Sketchup comedy group at the University of Maryland order a number of sketches into a full-length comedy show. Historically, the process of show ordering has been done by hand and typically takes multiple hours. This is because there are many (often competing) preferences that go into creating the best show order. For example:
* Sketches must be grouped in a number of blocks, with each block being roughly the same size
* There may be specific preferences for the first sketch of the show, for the last sketch of the show, or for pairs of sketches that should not be adjacent to one another
* It is desirable to minimize the number of times the same actor is in two adjacent sketches since this gives them a "quick change" between the sketches
  
Shows are typically arranged with alternating blocks of stage and video sketches. This model is designed specifically to order the stage sketches. (Ordering video sketches is typically much easier since the "quick change" problem does not exist for pre-recorded sketches.)

This task is also made more complex by the different types of sketches that may appear in a show. In addition to regular sketches, there are "diddies" (very short sketches) and "vignettes" (sets of about 3 short scenes that must be performed in a specific order at various points throughout the show). Each of these imposes additional constraints on the show order. 
## Model Objectives
This model is designed to guarnatee the following:
* It creates exactly the number of blocks as requested, with number of sketches in any 2 blocks differing by at most 1 (diddies/vignettes count as half sketches for this purpose)
* There are no triple changes (defined as an actor performing in 3 sequential sketches)
* Every set of vignettes appears in the correct order
* Each block has at most one vignette and at most one diddy
* Vignettes and diddies are not the first or last sketch overall
* Vignettes and diddies are never adjacent to other vignettes or diddies
* Certain sketches are placed at the start of blocks when this is specifically requested
* Certain pairs of sketches are not placed adjacent to one another when this is specifically requested
* Certain sketches are placed first or last overall when this is specifically requested
* Certain sketches are not placed in the first block when this is specifically requested
* No actor has more quick changes than the number allowed (given as input to model)
  
Simultaneously, the model will optimize for the following:
* Small number of quick changes overall
* Small number of times when two sketches with >= 5 or <= 2 actors appear adjacent to one another (each occurance of this carries the weight of 2 quick changes for optimization purposes)

Note the second of these items is a "soft" constraint by default but can be changed to a hard requirement using model parameters.

## Encoding Actors and Sketches
The ordering function, ```order```, takes as input a list of sketches, each containing a list of actors. Actors are encoded in the ``Actor`` class, while sketches are encoded in the ``Sketch``, ``Diddy``, and ``Vignette`` classes:

```python
alice = Actor("Alice") #provide actor's name as the only argument
bob = Actor("Bob")
charlie = Actor("Charlie")

aRegularSketch = Sketch("A Regular Sketch", [alice, bob, charlie]) #provide sketch name and list of actors in that sketch
aShortSketch = Diddy("A Very Short Sketch", [alice, bob]) #use the Diddy class for diddies

#For vignettes, provide a double-nested list. Each inner list corresponds to the actors in one vignette.
#Below, Alice and Bob are in the first vignette, while the second and third vignettes feature Bob and Charlie.
aSetOfVignettes = Vignettes("A Set of 3 Vignettes", [[alice, bob], [bob, charlie], [bob, charlie]])
```
## Model Parameters:
The driver function, ```order```, takes a number of parameters:
* ```sketches``` is a list of sketch objects. These are the sketches that the model will order.
* ```numBlocks``` is the number of stage blocks to create. Default: 4
* ```maxChangesPerActor``` is the maximum allowable number of quick changes per actor. Default: 3
* ```desiredFirstSketches``` is a list of sketches or ```None```. If a list is provided, the model will choose one of these sketches as the first in the show. Default: ```None```
* ```desiredLastSketches``` is similar to the above but for the last sketch in the show. Default: ```None```
* ```nonAdjacentSketches``` is a list of pairs of sketches or ```None```. If a list is provided, the model will ensure each pair ends up separated in the final order. Default: ```None```

  Usage: ```order(..., nonAdjacentSketches = [(sketch1, sketch2), (sketch1, sketch3)], ...)``` will ensure ```sketch1``` will not end up adjacent to either ```sketch2``` or ```sketch3```.
* ```blockStartingSketches``` is a list of sketches or ```None```. If a list is provided, the model will ensure every sketch in the list appears at the start of a block. Default: ```None```
* ```requireNoAdjacentSmalls``` is either ```True``` or ```False```. If ```True```, the model will ensure that no sketches with <= 2 actors end up adjacent to one another. If false, it will simply optimize for this, as described above. Default: ```False```
* ```requireNoAdjacentBigs``` is similar to the above but for sketches with >= 5 actors. Default: ```False```
* ```notInFirstBlock``` is either a list of sketches or ```None```. If a list is provided, the model will ensure every sketch in the list does not appear in the first block of the show (assuming ```numBlocks``` is greater than 1).
* ```timeout``` is the number of seconds the model should run for (see below). Default: ```60```
  
## A Note on Efficiency and Running Time
This program is built using the [Z3 optimizer](https://ericpony.github.io/z3py-tutorial/guide-examples.htm). This optimizer behaves much better with hard requirements than soft constraints. Namely, it can rather quickly find *a* show order that satisfies all hard requirements but, if left to its own devices, will spend a very long time optimizing for the soft constraints (few quick changes, few adjacent sketches with >= 5 or <= 2 actors). The ```timeout``` parameter is necessary so that after a certain amount of time, the orderer can stop running and return the best order it has found so far. If it has not had enough time to find *any* show order that satisfies all hard requirements, the program will print a message saying so. If no show order exists that satisfies all hard requirements, with enough time, the program will be able to prove this is the case and raise an ```Exception```. Since the model behaves better with hard constraints than soft ones, the best way to use it is probably to impose rather strict requirements (e.g. ```maxChangesPerActor = 1```).

Because this program uses Z3, you may have to run ```pip install z3-solver``` the first time you use it to download the Z3 optimizer.

## Full Example: Fall 2024 Show
```python
scott = Actor("Scott")
vincent = Actor("Vincent")
jesse = Actor("Jesse")
john = Actor("John")
edward = Actor("Edward")
simon = Actor("Simon")
fahran = Actor("Fahran")
mira = Actor("Mira")

bullies = Sketch("Bullies", [vincent, scott, jesse, john, edward])
doordash = Vignettes("Doordash", [[simon, scott], [scott, jesse], [scott, edward]])
call_me = Sketch("Here's my Number, so Call me Maybe", [john, mira, jesse, fahran])
chiv = Sketch("Chivalry isn't Dead", [vincent, scott, edward, jesse])
annapolis = Sketch("Annapolis", [edward, simon, john, jesse])
rollcall = Sketch("Roll Call", [simon, edward, fahran, mira, john])
cavemen = Sketch("Cavemen", [jesse, scott])
funeral = Sketch("Funeral", [scott, vincent, fahran, mira, simon])
fnaf = Sketch("Five Nights at Freddy's", [fahran, jesse, vincent, mira, john, simon])
greats = Sketch("Literary Greats", [fahran, mira, vincent, simon, john])
crossword = Sketch("Couples who Crossword", [fahran, simon, edward])
incognito = Sketch("Incognito Mode", [john, fahran, vincent, jesse, scott])
charlie = Sketch("A Very Charlie Brown Tax Season", [edward, mira, simon])
giftshop = Sketch("Gift Shop", [jesse, fahran, scott, vincent, simon])
tv = Diddy("TV", [edward, fahran])
firemen = Sketch("Firemen", [jesse, mira, vincent, scott, john])


sketches = [bullies, doordash, call_me, chiv, annapolis, rollcall, cavemen, funeral, fnaf, greats,
            crossword, incognito, charlie, giftshop, tv, firemen]

order(sketches, maxChangesPerActor = 1, desiredLastSketches = [rollcall], timeout = 60)
```
The program may behave differently each time it is run. However, one possible output of the above code is the following:
```
Checking inputs...
Encoding constraints...
Searching for show order...
Done.

Gift Shop: Jesse Fahran Scott Vincent Simon 
Here's my Number, so Call me Maybe: John Mira Jesse Fahran 
Doordash 1: Simon Scott 
Chivalry isn't Dead: Vincent Scott Edward Jesse 
---------------BLOCK---------------
Incognito Mode: John Fahran Vincent Jesse Scott 
A Very Charlie Brown Tax Season: Edward Mira Simon 
Doordash 2: Scott Jesse 
Literary Greats: Fahran Mira Vincent Simon John 
Bullies: Vincent Scott Jesse John Edward 
---------------BLOCK---------------
Five Nights at Freddy's: Fahran Jesse Vincent Mira John Simon 
Doordash 3: Scott Edward 
Annapolis: Edward Simon John Jesse 
Funeral: Scott Vincent Fahran Mira Simon 
---------------BLOCK---------------
TV: Edward Fahran 
Firemen: Jesse Mira Vincent Scott John 
Couples who Crossword: Fahran Simon Edward 
Cavemen: Jesse Scott 
Roll Call: Simon Edward Fahran Mira John
```
For change requests, bugs, or troubleshooting, feel free to submit a pull request or contact Fahran Bajaj at fahran.bajaj@gmail.com.
