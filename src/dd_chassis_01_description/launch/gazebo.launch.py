import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dd_chassis_01_description')
    urdf = os.path.join(pkg, 'urdf', 'test2_t03_DD_chassis_u_m.urdf')
    world = os.path.join(pkg, 'world', 'dd_chassis_01.world')
    with open(urdf) as f:
        robot_desc = f.read()

    env = dict(os.environ)
    env['IGN_GAZEBO_RESOURCE_PATH'] = (
        os.path.dirname(pkg) + ':'
        + env.get('IGN_GAZEBO_RESOURCE_PATH', ''))
    # WSLg 下 ogre2 渲染所需的三个变量（实测有效）
    env['MESA_D3D12_DEFAULT_ADAPTER_NAME'] = 'NVIDIA'   # 选 RTX 4060 独显
    env['MESA_GL_VERSION_OVERRIDE'] = '4.5'             # 绕过 Ogre2 copyTo 分支缺陷
    env['MESA_GLSL_VERSION_OVERRIDE'] = '450'

    return LaunchDescription([
        # Gazebo Fortress
        ExecuteProcess(
            cmd=['ign', 'gazebo', '-r', '-v', '4', '-s',
                 world],
            additional_env=env,
            output='screen'),

        ExecuteProcess(
            cmd=['ign', 'gazebo', '-v', '4', '-g'],
            additional_env=env,
            output='screen'),

        # 把 URDF 塞进 Gazebo
        ExecuteProcess(
            cmd=['ros2', 'run',
                 'ros_gz_sim', 'create',
                 '-world', 'default',
                 '-file', urdf,
                 '-name', 'dd_chassis',
                 '-z', '0.05'],
            additional_env=env,
            output='screen'),

        # Gazebo <-> ROS 话题桥，配置外置到 config/bridge.yaml
        Node(package='ros_gz_bridge',
             executable='parameter_bridge',
             parameters=[{'config_file':
                          os.path.join(pkg, 'config', 'bridge.yaml')}],
             additional_env=env,
             output='screen'),

        # 发布 robot_description（给 RViz / Nav2 用）
        Node(package='robot_state_publisher',
             executable='robot_state_publisher',
             parameters=[{'robot_description': robot_desc}],
             output='screen'),
    ])
