from neat import nn, population
from selenium import webdriver
import numpy as np
import os
import time
import Queue
import threading
import signal
MAX_SCOPE = 1000
from neat import nn, population, statistics
def inscope(snakepos, pos2):
    # if pos2[0] == snakepos[0] and pos2[1] == snakepos[1]:
    #     return False
    if calcDistance(snakepos, pos2) < MAX_SCOPE:
        return True
    return False

def getAngleIndex(snakepos, pos):
    radian = np.arctan((pos[1] - snakepos[1])/(pos[0] - snakepos[0] + 0.001))
    angle = radian*57.6
    angleIndex = np.floor(np.abs(angle/15.))
    if pos[0] - snakepos[0] >= 0 and pos[1] - snakepos[1] >= 0:
        return int(angleIndex)
    elif pos[0] - snakepos[0] >=0 and pos[1] -snakepos[1] < 0:
        return int(18 - angleIndex)
    elif pos[0] - snakepos[0] <0 and pos[1] - snakepos[1] >= 0:
        return int(6 - angleIndex)
    elif pos[0] - snakepos[0] <0 and pos[1] -snakepos[1] < 0:
        return int(12 + angleIndex)


def calcDistance(pos1, pos2):
    return np.sqrt(np.power(pos1[0]-pos2[0],2) + np.power(pos1[1]-pos2[1],2))


def scoreDistance(dis):
    return 1 - dis/MAX_SCOPE

def prepareInput(foods, thesnake, othersnake, grd):
    foodangle = []
    foodsize = []
    snakeangle = []
    blockangle = []
    snakepos = [thesnake['xx'], thesnake['yy']]
    for i in range(24):
        foodangle.append(0)
        foodsize.append(0)
        snakeangle.append(-1)
        blockangle.append(0)

    for food in foods:
        if food is None:
            continue
        foodpos = (food['xx'], food['yy'])
        if inscope(snakepos, foodpos):
            ind = getAngleIndex(snakepos, foodpos)
            dis = calcDistance(snakepos, foodpos)
            disscore = scoreDistance(dis)
            #print dis
            foodsz = food['sz']/30.
            if disscore > foodangle[ind]:
                foodangle[ind] = disscore
                foodsize[ind] = foodsz


    for sn in othersnake:
        if sn is None:
            continue
        if sn['id'] == thesnake['id']:
            continue
        snpos = (sn['xx'], sn['yy'])

        if inscope(snakepos, snpos):
            ind = getAngleIndex(snakepos, snpos)
            dis = (calcDistance(snakepos, snpos) - 29 * sn['sc'] )
            disscore = scoreDistance(dis)
            if disscore > blockangle[ind]:
                blockangle[ind] = disscore
                snakeangle[ind] = sn['ang']/(2*np.pi)

        for pts in sn['pts']:
            ptspos = (pts['xx'], pts['yy'])
            if inscope(snakepos, ptspos):
                ind = getAngleIndex(snakepos, ptspos)
                dis = calcDistance(snakepos, ptspos) - 29 * sn['sc']
                disscore = scoreDistance(dis)
                if disscore > blockangle[ind]:
                    blockangle[ind] = disscore
                    snakeangle[ind] = -1

    #Handle Wall
    if calcDistance(snakepos, (grd, grd)) > grd * 0.98 -1000:

        for i in range(24):
            testangle = 2*np.pi/24*i
            testpos = (snakepos[0] + 1500 * np.cos(testangle), snakepos[1] + 1500 * np.sin(testangle))
            if calcDistance(testpos, (grd, grd)) > grd * 0.98:
                blockangle[i] = 1 - (grd * 0.98 - calcDistance(snakepos, (grd, grd)))/1100.
                #print "Hitting the wall %d index distance:%s"%(i, blockangle[i])
                snakeangle[i] = -1




    return foodangle + foodsize + blockangle + snakeangle + snakepos



def evaluate(net, browser, agent):
    browser.get("http://slither.io")
    try:
        browser.execute_script("window.connect();window.render_mode = 1;window.want_quality = 0;window.high_quality = false;window.onmousemove = function(){};")
    except:
        print "Loading failure"
        time.sleep(3)
        return -1

    #window.redraw = function() {};
    retryNum = 0
    #lastScore = 0
    maxScore = 0
    startTime = time.time()
    maxTime = time.time()

    while True:
        aliveind = browser.execute_script("return window.dead_mtm")
        if aliveind is None:
            time.sleep(1)
            print "Connection error! Retry"
            return -1
        if aliveind == -1:
            foods = browser.execute_script("return window.foods")
            thesnake = browser.execute_script("return window.snake")
            othersnake = browser.execute_script("return window.snakes")
            grd = browser.execute_script("return window.grd")
            if thesnake is None or foods is None or othersnake is None:
                time.sleep(0.1)
                # print "Game not ready"
                retryNum += 1
                if retryNum > 100:
                    print "Agent %d Too many retry!"%agent
                    return -1
                continue

            rinput = prepareInput(foods, thesnake, othersnake, grd)
            snakeangle = (float)(thesnake['ang']) / (2*np.pi)
            rinput.append(snakeangle)
            #print rinput
            output = net.activate(rinput)
            acc =0
            maxv = 0.
            maxpos = 0
            for ki in range(24):
                if output[ki] > maxv:
                    maxv = output[ki]
                    maxpos = ki
            angle = 2 * np.pi / 24. * maxpos
            goalPos = (np.cos(angle) * 300, np.sin(angle) * 300)
            #print output[24]
            if output[24] > 0.7:
                acc = 1
            browser.execute_script(
                "window.xm = %s; window.ym = %s;window.setAcceleration(%d);" % (goalPos[0], goalPos[1], acc))
            score = browser.execute_script(
                "return Math.floor(15 * (fpsls[snake.sct] + snake.fam / fmlts[snake.sct] - 1) - 5)") / 10000.

            if maxScore < score:
                maxScore = score
                maxTime = time.time()
                    #print "Agent: %d MaxScore:%s" % (agent, maxScore)

            if time.time() - maxTime > 150 or time.time() - startTime > 600:
                print "Agent %d Reach Time Limit MaXscore:%s" % (agent,maxScore)
                break
            time.sleep(0.1)
        else:
            score = (float)(browser.execute_script("return window.lastscore.childNodes[1].innerHTML"))/10000.
            print "Agent %d Game stop! Final score: %s MAXScore %s"%(agent, score, maxScore)
            break
    return maxScore




def do_agent(genome):
    while True:
        #browser = webdriver.PhantomJS()
        browser = webdriver.Chrome()
        agent = 0
        net = nn.create_recurrent_phenotype(genome)

        while True:
            print "Agent %d starts working"%agent
            fitness_t1 = evaluate(net, browser, agent)
            if fitness_t1 > 0:
                #print("Agent %d get a fitness :%s" % (agent, fitness_t1))
                genome.fitness = fitness_t1
                break
            else:
                print ("Agent %d Evalution failed.! Retry!" % agent)
        #browser.service.process.send_signal(signal.SIGTERM)
        browser.quit()
        time.sleep(5)
        




def run():
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config')
    pop = population.Population(config_path)
    pop.load_checkpoint("neat-checkpoint-58")
    pop1 = []
    for s in pop.species:
        pop1.extend(s.members)
    for gn in pop1:
        do_agent(gn)



if __name__ == '__main__':
    run()
