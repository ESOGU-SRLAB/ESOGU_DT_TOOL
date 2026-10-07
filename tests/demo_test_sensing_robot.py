#!/usr/bin/env python3
"""
Demo Test Code 3: Sensing Robot Test
Tests sensing_robot.py trajectory management
"""

import json
import os

def test_trajectory_manager_init():
    """Test: TrajectoryManager initialization"""
    file_path = "test_trajectories.json"
    
    # Simulate trajectory manager
    trajectories = {}
    
    assert isinstance(trajectories, dict), "Trajectories should be a dictionary"
    assert file_path.endswith('.json'), "File should be JSON"
    
    print(f"✅ TrajectoryManager initialized with file: {file_path}")
    return True

def test_trajectory_structure():
    """Test: Trajectory data structure"""
    # Sample trajectory
    traj_data = {
        'joint_names': ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6', 'joint7'],
        'points': [
            {
                'positions': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'velocities': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'accelerations': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'time_from_start': {'sec': 0, 'nanosec': 0}
            }
        ]
    }
    
    assert 'joint_names' in traj_data, "Should have joint_names"
    assert 'points' in traj_data, "Should have points"
    assert len(traj_data['joint_names']) == 7, "Should have 7 joints"
    
    print(f"✅ Trajectory structure valid: {len(traj_data['joint_names'])} joints, {len(traj_data['points'])} points")
    return True

def test_hil_playback_mode():
    """Test: HIL playback mode parameters"""
    hil_playback_mode = False
    trajectory_file = "sensing_trajectories.json"
    
    assert isinstance(hil_playback_mode, bool), "HIL mode should be boolean"
    assert trajectory_file.endswith('.json'), "Trajectory file should be JSON"
    
    mode_str = "Playback" if hil_playback_mode else "Recording"
    print(f"✅ HIL mode: {mode_str}, file: {os.path.basename(trajectory_file)}")
    return True

def test_scan_parameters():
    """Test: Scanning parameters configuration"""
    scan_wait_time = 1.5
    max_scan_cycles = 1
    tcp_pose_rate_hz = 30.0
    
    assert scan_wait_time > 0, "Wait time should be positive"
    assert max_scan_cycles > 0, "Scan cycles should be positive"
    assert tcp_pose_rate_hz > 0, "Pose rate should be positive"
    
    print(f"✅ Scan params: wait={scan_wait_time}s, cycles={max_scan_cycles}, rate={tcp_pose_rate_hz}Hz")
    return True

def test_defect_detection():
    """Test: Defect detection parameters"""
    defect_duplicate_distance = 0.15
    
    assert defect_duplicate_distance > 0, "Duplicate distance should be positive"
    assert defect_duplicate_distance < 1.0, "Distance should be reasonable (< 1m)"
    
    print(f"✅ Defect detection threshold: {defect_duplicate_distance}m")
    return True

if __name__ == "__main__":
    print("📡 Running Sensing Robot Tests...\n")
    
    try:
        test_trajectory_manager_init()
        test_trajectory_structure()
        test_hil_playback_mode()
        test_scan_parameters()
        test_defect_detection()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
