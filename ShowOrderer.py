from z3 import *
import numpy.random

class Actor:
    def __init__(self, name: str):
        if not (isinstance(name, str)):
            raise TypeError("Actor name must be a string")
        self.name = name

class Sketch:
    def __init__(self, name, actors):
        if not (isinstance(name, str)):
            raise TypeError("Sketch name must be a string")
        seen = set([])
        if not (isinstance(actors, list)):
            raise TypeError("The second argument must be a list of actors in the sketch")
        for actor in actors:
            if not (isinstance(actor, Actor)):
                raise TypeError("Every element in list of actors must be of type Actor")
            if actor.name in seen:
                raise ValueError("Every actor in provided list must have a unique name")
            seen.add(actor.name)
            
        self.name = name
        self.actors = actors

class Diddy(Sketch):
    def __init__(self, name, actors):
        super().__init__(name, actors)

class Vignettes(Sketch):
    def __init__(self, name, actors):
        if not (isinstance(name, str)):
            raise TypeError("Name of vignettes must be a string")
        if not (isinstance(actors, list)):
            raise TypeError("The second argument must be a list where each element is a list of actors in a vignette")
        if len(actors) == 0:
            raise ValueError("Please provide the actors in at least 1 vignette")
        for vignette_actors in actors:
            if not (isinstance(vignette_actors, list)):
                raise TypeError("Every element in the second argument should be a list of actors")
            seen = set([])
            for actor in vignette_actors:
                if not (isinstance(actor, Actor)):
                    raise TypeError("Every element in list of actors must be of type Actor")
                if actor.name in seen:
                    raise ValueError("Every actor in list for given vignette must have a unique name")
                seen.add(actor.name)

        self.name = name
        self.actors = actors

#I'm sure this data structure exists but I don't know what it's called, so I'm making it myself
#Functions like a hash map but every key maps to a list of values. You can add to but not remove from list. You can get entire list at once.
class HashBag:
    def __init__(self):
        self.map = {}

    def add(self, key, value):
        if key in self.map.keys():
            lst = self.map[key]
            lst.append(value)
            self.map[key] = lst
        else:
            self.map[key] = [value]

    def get(self, key):
        if not(key in self.map.keys()):
            return []
        return self.map[key]

    def keys(self):
        return self.map.keys()

class ShowOrderer:
    def __init__(self, sketches):
        if not (isinstance(sketches, list)):
            raise TypeError("Please provide a list of sketches as the first argument to the driver.")

        seen = set([])
        for sketch in sketches:
            if not (isinstance(sketch, Sketch)):
                raise TypeError("Please provide a list of sketches as the first argument to the driver.")
            if sketch.name in seen:
                raise ValueError("Every sketch name must be unique")
            seen.add(sketch.name)

        self.sketches = numpy.random.permutation(sketches) #shuffle to get new starting point on different runs
        self.order = None

    #helper to make sure blocks are evenly sized
    def _blockSizing(self, blocks, vignettes_and_diddies, n_total):
        if not (isinstance(n_total, int)):
            raise TypeError("Last argument must be an integer representing number of sketches (each vignette counted as separate sketch) plus desired number of stage blocks minus 1")
        if n_total < len(blocks) + len(vignettes_and_diddies):
            raise ValueError("Last argument must be an integer representing number of sketches (each vignette counted as separate sketch) plus desired number of stage blocks minus 1")
        if not(isinstance(blocks, list)):
            raise TypeError("First argument must be list of z3 int variables corresponding to positions between stage blocks")
        for block in blocks:
            if not(isinstance(block, z3.z3.ArithRef) and block.is_int()):
                raise TypeError("Every element of first argument must be a z3 int variable")
        if not(isinstance(vignettes_and_diddies, list)):
            raise TypeError("Second argument must be list of z3 int variables corresponding to positions of vignettes and diddies")
        for sketch in vignettes_and_diddies:
            if not (isinstance(sketch, z3.z3.ArithRef) and sketch.is_int()):
                raise TypeError("Every element of second argument must be a z3 int variable")
    
        blocks.insert(0, 0) 
        blocks.append(n_total + 1) #adjust list of block positions so length of any stage block will be the difference between 2 list elems
    
        #compute length of each block
        block_lengths = []
        for block_num in range(1, len(blocks)):
            start_pos = blocks[block_num - 1]
            end_pos = blocks[block_num]
            length = end_pos - start_pos - 1
            for short_sketch in vignettes_and_diddies:
                length = length - 0.5*And(short_sketch > start_pos, short_sketch < end_pos) #vignettes/diddies count as half a sketch for length purposes
            block_lengths.append(length)
    
        #ensure lengths are within 1 of 1 another
        length_conditions = []
        for i in range(len(block_lengths)):
            for j in range(i + 1, len(block_lengths)):
                length_conditions.append(block_lengths[i] - block_lengths[j] <= 1)
                length_conditions.append(block_lengths[i] - block_lengths[j] >= -1)

        #no empty blocks, and block variables are in correct order
        for block_num in range(1, len(blocks)):
            length_conditions.append(blocks[block_num] - blocks[block_num - 1] > 1)
    
        return And(length_conditions)

    def _adjacent(self, x, y):
        if not (isinstance(x, z3.z3.ArithRef) and isinstance(y, z3.z3.ArithRef) and x.is_int() and y.is_int()):
            raise TypeError("Both inputs must be z3 integer variables")
    
        return Or(x - y == 1, x - y == -1)

    def _tripleChange(self, x, y, z):
        if not (isinstance(x, z3.z3.ArithRef) and isinstance(y, z3.z3.ArithRef) and isinstance(z, z3.z3.ArithRef) 
                and x.is_int() and y.is_int() and z.is_int()):
            raise TypeError("All inputs must be z3 integer variables")

        return Or(And(self._adjacent(x, y), self._adjacent(y, z)), And(self._adjacent(y, x), self._adjacent(x, z)), And(self._adjacent(y, z), self._adjacent(z, x)))

    def orderShow(self, numBlocks, maxChangesPerActor, desiredFirstSketches, desiredLastSketches, nonAdjacentSketches, 
                  differentBlockSketches, blockStartingSketches, requireNoAdjacentSmalls, requireNoAdjacentBigs, notInFirstBlock, timeout):
        #most input checking is done by driver function intended to call this one, but we'll take care of this real quick:
        if numBlocks > len(self.sketches):
            raise ValueError("Too many blocks, not enough sketches!")

        print("Encoding constraints...")
        s = Optimize() 
        s.set("timeout", timeout)
        #Ok, a couple notes on this "s" object:
        #This is an optimizer from the z3 library
        #We'll add a bunch of hard and soft constraints, and it will look for the best show order based on those constraints
        #This happens by adding an int variable corresponding to each sketch. It will assign each variable an integer based on constraints
            #we give it. Those integers correspond to a sketch's order in the show
        #(Makes sure to satisfy all of the hards and as many softs as possible, based on weighting of soft constraints)
        #"Timeout" parameter makes sure it stops after certain time with best order it has found so far
        #Otherwise it will search for a really long time looking for the best possible order
        #More info: https://ericpony.github.io/z3py-tutorial/
        
        #This section loops through all sketches and does a few things:
        #Create z3 integer variables for each sketch (or each vignette within a set)
        #Create map from an actor to all of their sketches so we can manage stuff like quick changes
        #Keep track of vignettes and diddies, big and small sketches for later requirements

        sketchVars = []
        blockVars = []
        actorsToSketches = HashBag()
        vignetteVars = []
        diddyVars = []
        largeSketches = []
        smallSketches = []
        
        for sketch in self.sketches:
            if isinstance(sketch, Vignettes):
                for (i, vignette_actors) in enumerate(sketch.actors):
                    name = sketch.name + " " + str(i + 1)
                    var = Int(name)
                    for actor in vignette_actors:
                        actorsToSketches.add(actor, var)
                    sketchVars.append(var)
                    vignetteVars.append(var)
                    if i > 0:
                        s.add(sketchVars[-1] > sketchVars[-2]) #make sure vignettes end up in proper order

                    #keep track of large, small sketches
                    if len(vignette_actors) <= 2:
                        smallSketches.append(var)
                    elif len(vignette_actors) >= 5:
                        largeSketches.append(var)
            else:
                var = Int(sketch.name)
                for actor in sketch.actors:
                    actorsToSketches.add(actor, var)
                sketchVars.append(var)
                if isinstance(sketch, Diddy):
                    diddyVars.append(var)

                #keep track of large, small sketches
                    if len(sketch.actors) <= 2:
                        smallSketches.append(var)
                    elif len(sketch.actors) >= 5:
                        largeSketches.append(var)

        for i in range(1, numBlocks):
            var = Int("Block " + str(i))
            blockVars.append(var)
        
        #every variable must be assigned to a unique and valid position
        n_total = len(sketchVars) + len(blockVars) #how many total variables to assign
        all_vars = sketchVars.copy()
        all_vars.extend(blockVars)
        for i in range(len(all_vars)):
            var1 = all_vars[i]
            s.add(var1 >= 1)
            s.add(var1 <= n_total)
            for j in range(i + 1, len(all_vars)):
                var2 = all_vars[j]
                s.add(var1 != var2)

        #make sure blocks are evenly sized
        vignettesAndDiddies = vignetteVars.copy()
        vignettesAndDiddies.extend(diddyVars)
        s.add(self._blockSizing(blockVars, vignettesAndDiddies, n_total)) 

        #no triple changes, minimize quick changes, make sure we don't exceed maximum quick changes
        for actor in actorsToSketches.keys():
            sketchList = actorsToSketches.get(actor)
            adjacencyVars = []
            for i in range(len(sketchList)):
                for j in range(i + 1, len(sketchList)):
                    s.add_soft(self._adjacent(sketchList[i], sketchList[j]), weight = -1)
                    adjacencyVars.append(self._adjacent(sketchList[i], sketchList[j]))
                    for k in range(j + 1, len(sketchList)):
                        s.add(Not(self._tripleChange(sketchList[i], sketchList[j], sketchList[k])))
            s.add(Sum(adjacencyVars) <= maxChangesPerActor)
                                                   
        #at most one vignette per block
        bookendedBlockNums = blockVars.copy()
        bookendedBlockNums.insert(0, 0)
        bookendedBlockNums.append(n_total + 1)
        for blockNum in range(1, len(bookendedBlockNums)):
            start_pos = bookendedBlockNums[blockNum - 1]
            end_pos = bookendedBlockNums[blockNum]
            vignettesInBlock = []
            for vignette in vignetteVars:
                vignettesInBlock.append(And(vignette > start_pos, vignette < end_pos))
            for i in range(len(vignettesInBlock)):
                #for each block b and vignette v, v in b ==> all other vignettes are not in b
                s.add(Implies(vignettesInBlock[i], Not(Or(Or(vignettesInBlock[:i]), Or(vignettesInBlock[i+1:])))))

        #at most one diddy per block
        for blockNum in range(1, len(bookendedBlockNums)):
            start_pos = bookendedBlockNums[blockNum - 1]
            end_pos = bookendedBlockNums[blockNum]
            diddiesInBlock = []
            for diddy in diddyVars:
                diddiesInBlock.append(And(diddy > start_pos, diddy < end_pos))
            for i in range(len(diddiesInBlock)):
                s.add(Implies(diddiesInBlock[i], Not(Or(Or(diddiesInBlock[:i]), Or(diddiesInBlock[i+1:])))))

        #vignettes and diddies are not first or last overall; vignettes and diddies are not adjacent
        for i, firstSketch in enumerate(vignettesAndDiddies):
            s.add(firstSketch != 1)
            s.add(firstSketch != n_total)
            for secondSketch in vignettesAndDiddies[i+1:]:
                s.add(Not(self._adjacent(firstSketch, secondSketch)))

        #Prefer no large or small sketches adjacent to one another
        if requireNoAdjacentBigs:
            def addBigConstraint(s1, s2):
                s.add(Not(self._adjacent(s1, s2)))
        else:
            def addBigConstraint(s1, s2):
                s.add_soft(Not(self._adjacent(s1, s2)), weight = 2)
        for i, firstSketch in enumerate(largeSketches):
            for secondSketch in largeSketches[i+1:]:
                addBigConstraint(firstSketch, secondSketch)

        if requireNoAdjacentSmalls:
            def addSmallConstraint(s1, s2):
                s.add(Not(self._adjacent(s1, s2)))
        else:
            def addSmallConstraint(s1, s2):
                s.add_soft(Not(self._adjacent(s1, s2)), weight = 2)
        for i, firstSketch in enumerate(smallSketches):
            for secondSketch in smallSketches[i+1:]:
                addSmallConstraint(firstSketch, secondSketch)
                
        #don't place specific sketches next to one another
        if not (nonAdjacentSketches is None):
            for (s1, s2) in nonAdjacentSketches:
                if (isinstance(s1, Vignettes) and isinstance(s2, Vignettes)) or isinstance(s1, Diddy) and isinstance(s2, Diddy):
                    #already handled this case
                    continue
                elif isinstance(s1, Vignettes):
                    var2 = s2.name
                    for i in range(len(s1.actors)):
                        name = s1.name + " " + str(i + 1)
                        var1 = Int(name)
                        s.add(Not(self._adjacent(var1, var2)))
                elif isinstance(s2, Vignettes):
                    #similar as above case but rewriting code for clarity
                    var1 = s1.name
                    for i in range(len(s2.actors)):
                        name = s2.name + " " + str(i + 1)
                        var1 = Int(name)
                        s.add(Not(self._adjacent(var1, var2)))
                else:
                    s.add(Not(self._adjacent(Int(s1.name), Int(s2.name))))

        #place certain sketches in different blocks from one another
        if not (differentBlockSketches is None):
            for (s1, s2) in differentBlockSketches:
                if (isinstance(s1, Vignettes) or isinstance(s2, Vignettes)):
                    raise Exception("Putting vignettes in differentBlockSketches is not supported.")
                else:
                    separators = []
                    s1var = Int(s1.name)
                    s2var = Int(s2.name)
                    for var in blockVars:
                        separators.append(Or(And(s1var > var, s2var < var), And(s1var < var, s2var > var)))

                    s.add(Or(separators))

        #place specific sketches first or last
        if not(desiredFirstSketches is None):
            firstSketchConstraints = []
            for sketch in desiredFirstSketches:
                if isinstance(sketch, Diddy) or isinstance(sketch, Vignettes):
                    raise Exception("This model is designed to not have diddies or vignettes as the first overall sketch.")
                firstSketchConstraints.append(Int(sketch.name) == 1)
            s.add(Or(firstSketchConstraints))

        if not(desiredLastSketches is None):
            lastSketchConstraints = []
            for sketch in desiredLastSketches:
                if isinstance(sketch, Diddy) or isinstance(sketch, Vignettes):
                    raise Exception("This model is designed to not have diddies or vignettes as the last overall sketch.")
                lastSketchConstraints.append(Int(sketch.name) == n_total)
            s.add(Or(lastSketchConstraints))

        #Place specific sketches at start of blocks
        if not(blockStartingSketches is None):
            for blockStartingSketch in blockStartingSketches:
                if isinstance(blockStartingSketch, Vignettes):
                    #do they want all vignettes at start of the block? Just one in particular?
                    raise Exception("Putting vignettes in blockStartingSketches is not supported.") 
                constraints = [Int(blockStartingSketch.name) == 1]
                for blockVar in blockVars:
                    constraints.append(Int(blockStartingSketch.name) == blockVar + 1)
                s.add(Or(constraints))

        #Don't place specific sketches in the first block
        if not(notInFirstBlock is None):
            for sketch in notInFirstBlock:
                if numBlocks > 1:
                    if isinstance(sketch, Vignettes):
                        s.add(blockVars[0] < Int(sketch.name + " 1"))
                    else:
                        s.add(blockVars[0] < Int(sketch.name))

        print("Searching for show order...")
        model = s.check()
        if model == unsat:
            raise Exception("There are no show orders that satisfy all hard constraints. Try loosening hard constraints.")
        return s.model()

    def print_order(self, model, sketchesToActors):
        if len(model) == 0:
            print("Could not find a show order that satisfies all hard constraints within the time allotted. Try loosening hard constraints or increasing time limit.")
            return
            
        print("Done.\n")
        numsToSketches = {}
        for var in model:
            numsToSketches[model[var].as_long()] = var

        for i in range(1, len(model) + 1):
            sketch = str(numsToSketches[i])
            if sketch[:5] == "Block":
                print("---------------BLOCK---------------")
            else: 
                print(sketch, end = ": ")
                for actor in sketchesToActors[sketch]:
                    print(actor.name, end = " ")
                print("")

def order(sketches, numBlocks = 4, maxChangesPerActor = 3, desiredFirstSketches = None, desiredLastSketches = None, 
          nonAdjacentSketches = None, differentBlockSketches = None, blockStartingSketches = None, requireNoAdjacentSmalls = False, 
          requireNoAdjacentBigs = False, notInFirstBlock = None, timeout = 60):
    print("Checking inputs...")
    orderer = ShowOrderer(sketches)

    #input checking: (sketches parameter is already checked by init of ShowOrderer class)
    if not isinstance(numBlocks, int):
        raise TypeError("Please provide a positive integer number of blocks")
    if numBlocks <= 0:
        raise ValueError("Please provide a positive integer number of blocks")
    if not isinstance(maxChangesPerActor, int):
        raise TypeError("Please provide a nonnegative integer number of max quick changes per actor")
    if maxChangesPerActor < 0:
        raise ValueError("Please provide a nonnegative integer number of max quick changes per actor")

    #create a function that can check desiredFirstSketches, desiredLastSketches, and blockStartingSketches at once
    def checkList(listOfSketches, parameterName):
        if not (listOfSketches is None):
            if not isinstance(listOfSketches, list):
                raise TypeError(parameterName + " must be a list of sketches (or None)")
            for sketch in listOfSketches:
                if not isinstance(sketch, Sketch):
                    raise TypeError(parameterName + " must be a list of sketches (or None)")
                if not (sketch in sketches):
                    raise ValueError("Every sketch in " + parameterName + " must be in the list of sketches you provided.")

    checkList(desiredFirstSketches, "desiredFirstSketches")
    checkList(desiredLastSketches, "desiredLastSketches")
    checkList(blockStartingSketches, "blockStartingSketches")
    checkList(notInFirstBlock, "notInFirstBlock")

    #create a function that can check nonAdjacentSketches and differentBlockSketches at once

    def checkListOfTuples(listOfTuples, parameterName):
        if not (listOfTuples is None):
            if not isinstance(listOfTuples, list):
                raise TypeError(parameterName + " must be a list of pairs (tuples) of sketches (or None)")
            for pair in listOfTuples:
                if not(len(pair) == 2 and isinstance(pair[0], Sketch) and isinstance(pair[1], Sketch)):
                    raise TypeError(parameterName + " must be a list of pairs (tuples) of sketches (or None)")
                if not(pair[0] in sketches and pair[1] in sketches):
                    raise ValueError("Every sketch in " + parameterName + " must be in the list of sketches you provided.")

    checkListOfTuples(nonAdjacentSketches, "nonAdjacentSketches")
    checkListOfTuples(differentBlockSketches, "differentBlockSketches")
    
    #check requireNoAdjacentSmalls, requireNoAdjacentBigs
    if not isinstance(requireNoAdjacentSmalls, bool):
        raise TypeError("requireNoAdjacentSmalls must be True or False")
    if not isinstance(requireNoAdjacentBigs, bool):
        raise TypeError("requireNoAdjacentBigs must be True or False")

    #create order
    model = orderer.orderShow(numBlocks, maxChangesPerActor, desiredFirstSketches, desiredLastSketches, nonAdjacentSketches, 
                              differentBlockSketches, blockStartingSketches, requireNoAdjacentSmalls, requireNoAdjacentBigs, notInFirstBlock, 
                              timeout * 1000)

    #print order
    names = {}
    for sketch in sketches:
        if isinstance(sketch, Vignettes):
            for i in range(len(sketch.actors)):
                names[sketch.name + " " + str(i + 1)] = sketch.actors[i]
        names[sketch.name] = sketch.actors
    
    orderer.print_order(model, names)
    
#------------------------------EXAMPLE: FALL 2024 SHOW------------------------------
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


sketches = [bullies, doordash, call_me, chiv, annapolis, rollcall, cavemen, funeral, fnaf, greats, crossword, incognito, charlie, giftshop,
           tv, firemen]

order(sketches, maxChangesPerActor = 1, desiredLastSketches = [rollcall], timeout = 60)
