# add parent dir to find package. Only needed for source code build, pip install doesn't need it.
import os, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
os.sys.path.insert(0, parentdir)

import gym
from realenv.envs.husky_env import HuskyFlagRunEnv

from baselines import deepq
import matplotlib.pyplot as plt
import datetime


def callback(lcl, glb):
    # stop training if reward exceeds 199
    total = sum(lcl['episode_rewards'][-101:-1]) / 100
    totalt = lcl['t']
    is_solved = totalt > 20 and total >= 80
    return is_solved


def main():
    env = HuskyFlagRunEnv(human=True, is_discrete=True, enable_sensors=True)
    model = deepq.models.mlp([64])
    act = deepq.learn(
        env,
        q_func=model,
        lr=1e-3,
        max_timesteps=100000,
        buffer_size=50000,
        exploration_fraction=0.1,
        exploration_final_eps=0.02,
        print_freq=10,
        callback=callback
    )
    print("Saving model to husky_flagrun_model.pkl")
    act.save("husky_flagrun_model.pkl")


if __name__ == '__main__':
    main()