#add parent dir to find package. Only needed for source code build, pip install doesn't need it.
import os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
os.sys.path.insert(0,parentdir)

import tensorflow as tf
import gym, logging
from mpi4py import MPI
from realenv.envs.husky_env import HuskyNavigateEnv
from baselines.common import set_global_seeds
import pposgd_simple
import baselines.common.tf_util as U
import cnn_policy
import utils
import datetime
from baselines import logger
from baselines import bench
import os.path as osp
import random

## Training code adapted from: https://github.com/openai/baselines/blob/master/baselines/ppo1/run_atari.py

def enjoy(num_timesteps, seed):
    sess = tf.Session()
    init_op = tf.global_variables_initializer()

    if args.meta != "":
        saver = tf.train.import_meta_graph(args.meta)
        saver.restore(sess,tf.train.latest_checkpoint('./'))

    workerseed = seed + 10000 * MPI.COMM_WORLD.Get_rank()
    set_global_seeds(workerseed)

    env = HuskyNavigateEnv(human=True, is_discrete=True, mode=args.mode, gpu_count=args.gpu_count, use_filler=not args.disable_filler)
    env = bench.Monitor(env, logger.get_dir() and
        osp.join(logger.get_dir(), str(rank)))
    env.seed(workerseed)
    
    #policy = cnn_policy.CnnPolicy(name='pi', ob_space=env.observation_space, ac_space=env.action_space, save_per_acts=10000, session=sess)
    def policy_fn(name, ob_space, ac_space):
        return cnn_policy.CnnPolicy(name=name, ob_space=ob_space, ac_space=ac_space, save_per_acts=10000, session=sess)

    policy = policy_fn("pi", env.observation_space, env.action_space) # Construct network for new policy
    def execute_policy(env):
        ob, ob_sensor = env.reset()
        stochastic=True
        while True:
            #with Profiler("agent act"):
            ac, vpred = policy.act(stochastic, ob)
            ob, rew, new, _ = env.step(ac)
            if new:
                ob, ob_sensor = env.reset()

    gym.logger.setLevel(logging.WARN)
    sess.run(init_op)
    execute_policy(env)
    env.close()


def callback(lcl, glb):
    # stop training if reward exceeds 199
    total = sum(lcl['episode_rewards'][-101:-1]) / 100
    totalt = lcl['t']
    is_solved = totalt > 2000 and total >= -50
    return is_solved



def main():
 
    #with tf.Session(graph=tf.Graph()) as sess:
    #  tf.saved_model.loader.load(sess, 'cnn_policy', args.dir)
    #all_vars = tf.get_collection('vars')
    #for v in all_vars:
    #    v_ = sess.run(v)
    #    print(v_)
    enjoy(num_timesteps=1000000, seed=5)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--mode', type=str, default="DEPTH")
    parser.add_argument('--num_gpu', type=int, default=1)
    parser.add_argument('--gpu_count', type=int, default=0)
    parser.add_argument('--disable_filler', action='store_true', default=False)
    parser.add_argument('--meta', type=str, default="")
    args = parser.parse_args()

    main()