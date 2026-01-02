#!/usr/bin/env python3
"""
纯净版安装脚本 - 使用清华镜像源安装Python包
"""

import subprocess
import sys

def install_with_mirror(package_name):
    """使用清华镜像源安装包"""
    mirror_url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
    
    print(f"正在使用清华镜像源安装 {package_name}...")
    print(f"镜像地址: {mirror_url}")
    print("-" * 50)
    
    try:
        cmd = [
            sys.executable, "-m", "pip", "install",
            "-i", mirror_url,
            "--trusted-host", "mirrors.tuna.tsinghua.edu.cn",
            package_name
        ]
        
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        
        # 检查是否已安装
        if "already satisfied" in result.stdout.lower():
            print(f"ℹ️  {package_name} 已安装，无需重复安装")
        else:
            print(f"✅ {package_name} 安装成功！")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败！")
        if e.stderr:
            error_msg = e.stderr[:200]
            print("错误:", error_msg)
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        # 安装命令行指定的所有包
        packages = sys.argv[1:]
    else:
        # 默认安装列表（可以修改这里）
        packages = [
            "optuna",           # 超参数优化
            "realesrgan",  # 
        ]
    
    if packages:
        print(f"准备安装 {len(packages)} 个包:")
        for pkg in packages:
            print(f"  - {pkg}")
        print()
    
    success_count = 0
    for package in packages:
        if install_with_mirror(package):
            success_count += 1
        print()  # 空行分隔
    
    if packages:
        print(f"安装完成！成功: {success_count}/{len(packages)}")
    else:
        print("未指定要安装的包，使用方法:")
        print("  python 脚本.py <包名1> <包名2> ...")
        print("示例:")
        print("  python 脚本.py numpy pandas")
        print("  python 脚本.py scikit-learn==1.3.0")

if __name__ == "__main__":
    main()