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
* No actor has more quick changes than the number allowed (given as input to model)
  
Simultaneously, the model will optimize for the following:
* Small number of quick changes overall
* Small number of times when two sketches with >= 5 or <= 2 actors appear adjacent to one another (each occurance of this carries the weight of 2 quick changes for optimization purposes)

Note the second of these items is a "soft" constraint by default but can be changed to a hard requirement using model parameters.

## Encoding Actors and Sketches
The ordering function takes as input a list of sketches, each containing a list of actors. Actors are encoded in the ``Actor`` class, while sketches are encoded in the ``Sketch``, ``Diddy``, and ``Vignette`` classes:

    alice = Actor("Alice") #provide actor's name as the only argument
    bob = Actor("Bob")
    charlie = Actor("Charlie")

    
