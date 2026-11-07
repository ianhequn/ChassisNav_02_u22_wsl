import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dd_chassis_01_description')
    slam_pkg = get_package_share_directory('slam_toolbox')
    nav2_pkg = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')
    params_file = LaunchConfiguration('params_file')
    slam_params_file = LaunchConfiguration('slam_params_file')

    rviz_config = os.path.join(
        nav2_pkg, 'rviz', 'nav2_default_view.rviz')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(pkg, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(pkg, 'config', 'slam_lifelong.yaml')),

        
        # 注意：joint_state_broadcaster / diff_drive_controller 的 spawner
        # 以及 /cmd_vel -> /cmd_vel_unstamped 的 relay，都已经移到
        # gazebo.launch.py 里。
        #
        # 原因：底盘控制器的生命周期应该跟 Gazebo 绑定，而不是跟导航栈绑定。
        # 放这边会导致“只启动 gazebo.launch.py 时遥控无效”；
        # 而且两个 launch 都起时会重复 spawn、重复 relay。
        # 现在职责划分：
        #   gazebo.launch.py   -> Gazebo + 桥 + 控制器 + relay（底盘可控）
        #   slam_nav2.launch.py -> EKF + 雷达过滤 + SLAM + Nav2 + RViz

        # 雷达过滤：屏蔽车体自身
        # 读 /scan_raw（Gazebo 桥进来的原始数据），写 /scan（slam 和 costmap 用）
        Node(
            package='laser_filters',
            executable='scan_to_scan_filter_chain',
            name='scan_filter',
            output='screen',
            parameters=[
                os.path.join(pkg, 'config', 'scan_filter.yaml'),
                {'use_sim_time': use_sim_time},
            ],
            remappings=[('scan', 'scan_raw'), ('scan_filtered', 'scan')],
        ),

        # EKF：轮速 + IMU -> odom -> base_footprint
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[
                os.path.join(pkg, 'config', 'ekf.yaml'),
                {'use_sim_time': use_sim_time},
            ],
            remappings=[('odometry/filtered', 'odom')],
        ),

        # slam_toolbox 终身建图
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[
                slam_params_file,
                {'use_sim_time': use_sim_time},
            ],
        ),

        # Nav2（不含 map_server / amcl，地图由 slam_toolbox 提供）
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_pkg, 'launch', 'navigation_launch.py')),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'params_file': params_file,
                'autostart': 'true',
                'use_composition': 'False',
            }.items(),
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(use_rviz),
            output='screen',
        ),
    ])
