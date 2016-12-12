from neat import nn, population
from selenium import webdriver
import numpy as np
import os
import time
import Queue
import threading
import signal
MAX_SCOPE = 1000
threadQ = Queue.Queue()
threadSize = 1

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

def prepareInput(foods, thesnake, othersnake, grd):
    foodangle = []
    foodsize = []
    snakeangle = []
    blockangle = []
    snakepos = [thesnake['xx'], thesnake['yy']]
    for i in range(24):
        foodangle.append(-1)
        foodsize.append(-1)
        snakeangle.append(-1)
        blockangle.append(-1)

    for food in foods:
        if food is None:
            continue
        foodpos = (food['xx'], food['yy'])
        if inscope(snakepos, foodpos):
            ind = getAngleIndex(snakepos, foodpos)
            dis = calcDistance(snakepos, foodpos) / (MAX_SCOPE)
            #print dis
            foodsz = food['sz']/30.
            if dis < foodangle[ind] or foodangle[ind] == -1:
                foodangle[ind] = dis
                foodsize[ind] = foodsz


    for sn in othersnake:
        if sn is None:
            continue
        if sn['id'] == thesnake['id']:
            continue
        snpos = (sn['xx'], sn['yy'])

        if inscope(snakepos, snpos):
            ind = getAngleIndex(snakepos, snpos)
            dis = (calcDistance(snakepos, snpos) - 29 * sn['sc'] ) / MAX_SCOPE
            if dis < blockangle[ind] or blockangle[ind] == -1:
                blockangle[ind] = dis
                snakeangle[ind] = sn['ehang']

        for pts in sn['pts']:
            ptspos = (pts['xx'], pts['yy'])
            if inscope(snakepos, ptspos):
                ind = getAngleIndex(snakepos, ptspos)
                dis = calcDistance(snakepos, ptspos) / MAX_SCOPE
                if dis < blockangle[ind] or blockangle[ind] == -1:
                    blockangle[ind] = dis
                    snakeangle[ind] = -1

    #Handle Wall
    if calcDistance(snakepos, (grd, grd)) > grd * 0.98 -1000:

        for i in range(24):
            testangle = 2*np.pi/24*i
            testpos = (snakepos[0] + 1500 * np.cos(testangle), snakepos[1] + 1500 * np.sin(testangle))
            if calcDistance(testpos, (grd, grd)) > grd * 0.98:
                blockangle[i] = (grd * 0.98 - calcDistance(snakepos, (grd, grd)))/1100.
                #print "Hitting the wall %d index distance:%s"%(i, blockangle[i])
                snakeangle[i] = -1




    return foodangle + foodsize + blockangle + snakeangle + snakepos



def evaluate(net, browser, agent):
    browser.get("http://slither.io")
    browser.execute_script(
        "window.connect();window.render_mode = 1;window.want_quality = 0;window.high_quality = false;window.onmousemove = function(){};")
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
                    print "Too many retry!"
                    return -1
                continue

            rinput = prepareInput(foods, thesnake, othersnake, grd)
            snakeangle = (float)(thesnake['ehang']) / (np.pi)
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

            if time.time() - maxTime > 120 or time.time() - startTime > 900:
                print "Agent %d Reach Time Limit MaXscore:%s" % (agent,maxScore)
                break
            time.sleep(0.1)
        else:
            score = (float)(browser.execute_script("return window.lastscore.childNodes[1].innerHTML"))/10000.
            print "Agent %d Game stop! Final score: %s MAXScore %s"%(agent, score, maxScore)
            break
    return maxScore



def do_agent():
    while True:
        #browser = webdriver.PhantomJS()
        browser = webdriver.Chrome()
        item = threadQ.get()
        genome = item[0]
        agent = item[1]
        net = nn.create_recurrent_phenotype(genome)
        fitness_t1 = 0.
        while True:
            print "Agent %d starts working"%agent
            fitness_t1 = evaluate(net, browser, agent)
            if fitness_t1 > 0:
                #print("Agent %d get a fitness :%s" % (agent, fitness_t1))
                genome.fitness = fitness_t1
                break
            else:
                print ("Agent %d Evalution failed.! Retry!" % agent)
        browser.service.process.send_signal(signal.SIGTERM)
        browser.quit()
        threadQ.task_done()



def dispatcher(genomes):
    agent_id = 0
    for g in genomes:
        agent_id += 1
        threadQ.put([g, agent_id])
    threadQ.join()

def run():
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config')
    pop = population.Population(config_path)
    pop.load_checkpoint("neat-checkpoint-58")
    pop.run(dispatcher, 400)



if __name__ == '__main__':
    for i in range(threadSize):
        t = threading.Thread(target=do_agent)
        t.start()
    run()
