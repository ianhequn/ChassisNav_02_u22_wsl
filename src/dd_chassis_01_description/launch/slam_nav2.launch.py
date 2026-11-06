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

        
        # joint_state_broadcaster：先把 /joint_states 发出来
        Node(
            package='controller_manager', executable='spawner',
            arguments=['joint_state_broadcaster'],
            output='screen',
        ),

        # diff_drive_controller：订阅 cmd_vel_unstamped，发布 odom
        Node(
            package='controller_manager', executable='spawner',
            arguments=['diff_drive_controller'],
            output='screen',
        ),

        # /cmd_vel_smoothed -> /diff_drive_controller/cmd_vel_unstamped
        #
        # nav2 标准链路：controller_server -> /cmd_vel
        #   -> velocity_smoother -> /cmd_vel_smoothed -> 底盘。
        # relay 若直接接 /cmd_vel，就把平滑器整个旁路了：
        #   - 加减速限幅失效，底盘收到阶跃指令
        #   - /cmd_vel_smoothed 无人订阅，velocity_smoother 白跑
        # 接 smoothed 后遥控和导航走同一道平滑，行为一致。
        # 代价：只跑 gazebo.launch.py 不开 nav2 时没有 velocity_smoother，
        #       遥控会失效。
        Node(
            package='topic_tools', executable='relay',
            name='cmd_vel_relay',
            arguments=['/cmd_vel_smoothed',
                       '/diff_drive_controller/cmd_vel_unstamped'],
            output='screen',
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
