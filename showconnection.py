from neat import nn, population
from selenium import webdriver
import numpy as np
import os
import time
import Queue
import threading
import signal


def dispatcher(genomes):
    agent_id = 0
    for g in genomes:
	print g
	time.sleep(20)

def run():
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config')
    pop = population.Population(config_path)
    pop.load_checkpoint("neat-checkpoint-111")
    pop.run(dispatcher, 1)



if __name__ == '__main__':
    run()
