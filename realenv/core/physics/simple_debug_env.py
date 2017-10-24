## Issue related to time resolution/smoothness
#  http://bulletphysics.org/mediawiki-1.5.8/index.php/Stepping_The_World

import pybullet as p
import time
import random
import zmq
import argparse
import os
import json
import numpy as np
import settings
from transforms3d import euler, quaternions
from realenv.core.physics.physics_object import PhysicsObject
from realenv.core.render.profiler import Profiler
from numpy import sin, cos


class PhysRenderer(object):

    def __init__(self, obj_path, framePerSec, debug, human):
        context = zmq.Context()
        
        self.debug_sliders = {}

        if debug:
            p.connect(p.GUI)
            p.configureDebugVisualizer(p.COV_ENABLE_KEYBOARD_SHORTCUTS, 0)
            self._startDebugRoomMap()
        else:
            # Headless training mode
            p.connect(p.DIRECT)

        p.setRealTimeSimulation(0)

        collisionId = p.createCollisionShape(p.GEOM_MESH, fileName=obj_path, meshScale=[1, 1, 1], flags=p.GEOM_FORCE_CONCAVE_TRIMESH)

        if debug:
            visualId = p.createVisualShape(p.GEOM_MESH, fileName=obj_path, meshScale=[1, 1, 1], rgbaColor = [1, 0.2, 0.2, 0.3], specularColor=[0.4, 4.0])
            boundaryUid = p.createMultiBody(baseCollisionShapeIndex = collisionId, baseVisualShapeIndex = visualId)
            print("Exterior boundary", boundaryUid)
            p.changeVisualShape(boundaryUid, -1, rgbaColor=[1, 0.2, 0.2, 0.3], specularColor=[1, 1, 1])
            #p.changeVisualShape(visualId, -1, rgbaColor=[1, 0.2, 0.2, 0.3])
        else:
            visualId = 0

        #p.setGravity(0,0,-10)
        p.setRealTimeSimulation(0)
        self.framePerSec = framePerSec

        file_dir = os.path.dirname(os.path.abspath(__file__))
        self.objectUid = p.loadURDF(os.path.join(file_dir, "models/quadrotor.urdf"), globalScaling = 0.8)
        #self.objectUid = p.loadURDF(os.path.join(file_dir, "models/husky.urdf"), globalScaling = 0.8)

        self.viewMatrix = p.computeViewMatrixFromYawPitchRoll([0, 0, 0], 10, 0, 90, 0, 2)
        self.projMatrix = p.computeProjectionMatrix(-0.01, 0.01, -0.01, 0.01, 0.01, 128)
        p.getCameraImage(256, 256, viewMatrix = self.viewMatrix, projectionMatrix = self.projMatrix)

        self.target_pos = np.array([-4.35, -1.71, 0.8])
        self.human = human

    def initialize(self, pose):
        pos, quat_xyzw = pose[0], pose[1]
        v_t = 1             # 1m/s max speed
        v_r = np.pi/5       # 36 degrees/s
        self.cart = PhysicsObject(self.objectUid, p, pos, quat_xyzw, v_t, v_r, self.framePerSec)
        print("Generated cart", self.objectUid)
        #p.setTimeStep(1.0/framePerSec)
        p.setTimeStep(1.0/settings.STEPS_PER_SEC)

    def _camera_init_orientation(self, quat):
        to_z_facing = euler.euler2quat(np.pi/2, np.pi, 0)
        return quaternions.qmult(to_z_facing, quat_wxyz)

    def _setPosViewOrientation(objectUid, pos, rot):
        return

    def _stepNsteps(self, N, pObject):
        for _ in range(N):
            p.stepSimulation()
            pObject.parseActionAndUpdate()
        pObject.clearUpDelta()

    def _startDebugRoomMap(self):
        cameraDistSlider  = p.addUserDebugParameter("Distance",0,15,4)
        cameraYawSlider   = p.addUserDebugParameter("Camera Yaw",-180,180,-45)
        cameraPitchSlider = p.addUserDebugParameter("Camera Pitch",-90,90,-30)
        self.debug_sliders = {
            'dist' :cameraDistSlider,
            'yaw'  : cameraYawSlider,
            'pitch': cameraPitchSlider
        }

    def renderOffScreen(self, action, restart=False):
        ## Execute one frame
        #print("physics engine get action", action)
        self.cart.parseActionAndUpdate(action)

        self._stepNsteps(int(settings.STEPS_PER_SEC/self.framePerSec), self.cart)
        pos_xyz, quat_wxyz = self.cart.getViewPosAndOrientation()
        state = {
            'distance_to_target': np.sum(np.square(pos_xyz - self.target_pos))
        }
        return [pos_xyz, quat_wxyz], state

    def renderToScreen(self, action, restart=False):
        
        if self.human:
            self.cart.getUpdateFromKeyboard(restart=restart)
        else:
            self.cart.parseActionAndUpdate(action)

        self._stepNsteps(int(settings.STEPS_PER_SEC/self.framePerSec), self.cart)
        
        pos_xyz, quat_wxyz = self.cart.getViewPosAndOrientation()
        
        cameraDist = p.readUserDebugParameter(self.debug_sliders['dist'])
        cameraYaw  = p.readUserDebugParameter(self.debug_sliders['yaw'])
        cameraPitch = p.readUserDebugParameter(self.debug_sliders['pitch'])
        
        p.getCameraImage(256, 256, viewMatrix = self.viewMatrix, projectionMatrix = self.projMatrix)
        p.resetDebugVisualizerCamera(cameraDist, cameraYaw, cameraPitch, pos_xyz)
        
        state = {
            'distance_to_target': np.sum(np.square(pos_xyz - self.target_pos))
        }
        
        return [pos_xyz, quat_wxyz], state


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--objpath'  , required = True, help='dataset path')
    opt = parser.parse_args()

    framePerSec = 13

    r_physics = PhysRenderer(opt.objpath, framePerSec)
    r_physics.initialize(pose_init)
    r_physics.renderToScreen()
        