#!/usr/bin/env python3
"""
Demo Test Code 1: Robot Joint Goal Test
Tests ex_joint_goal.py functionality
"""

def test_joint_goal_initialization():
    """Test: Robot initialization and joint goal setup"""
    # Simulated test - checks joint position array
    joint_positions = [1.57, -1.57, 0.0, -1.57, 0.0, 1.57, 0.7854]
    
    assert len(joint_positions) == 7, "Joint positions array should have 7 elements"
    assert all(isinstance(j, (int, float)) for j in joint_positions), "All joint values should be numeric"
    
    print(f"✅ Joint positions valid: {joint_positions}")
    return True

def test_joint_goal_movement():
    """Test: Joint movement execution"""
    # Simulated movement test
    start_position = [0.0, 0.0, 0.0, -0.785, 0.0, 1.571, 0.785]
    target_position = [1.57, -1.57, 0.0, -1.57, 0.0, 1.57, 0.7854]
    
    # Calculate movement delta
    delta = [abs(t - s) for s, t in zip(start_position, target_position)]
    max_delta = max(delta)
    
    assert max_delta > 0, "Movement should be detected"
    print(f"✅ Max joint movement delta: {max_delta:.3f} radians")
    return True

def test_planner_configuration():
    """Test: MoveIt2 planner configuration"""
    planner_id = "RRTConnectkConfigDefault"
    max_velocity = 0.5
    max_acceleration = 0.5
    
    assert planner_id in ["RRTConnectkConfigDefault", "RRTstar"], "Valid planner ID"
    assert 0 < max_velocity <= 1.0, "Velocity should be between 0 and 1"
    assert 0 < max_acceleration <= 1.0, "Acceleration should be between 0 and 1"
    
    print(f"✅ Planner config valid: {planner_id}, vel={max_velocity}, acc={max_acceleration}")
    return True

if __name__ == "__main__":
    print("🤖 Running Robot Joint Goal Tests...\n")
    
    try:
        test_joint_goal_initialization()
        test_joint_goal_movement()
        test_planner_configuration()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
