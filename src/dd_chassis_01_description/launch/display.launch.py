import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dd_chassis_01_description')
    urdf = os.path.join(pkg, 'urdf', 'test2_t03_DD_chassis_u_m.urdf')
    with open(urdf) as f:
        robot_desc = f.read()

    return LaunchDescription([
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             parameters=[{'robot_description': robot_desc}],
             output='screen'),

        Node(package='joint_state_publisher_gui', 
             executable='joint_state_publisher_gui'),

        Node(package='rviz2',
             executable='rviz2',
             arguments=['-d', 
                    os.path.join(pkg, 
                    'launch', 'display.rviz')]),
    ])


