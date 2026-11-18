#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main(int argc, char *argv[]) {
    // 檢查是否為 root (setuid 生效後 euid=0)
    if (geteuid() != 0) {
        fprintf(stderr, "Error: must run as root (setuid required)\n");
        return 1;
    }
    
    // 構建命令
    char *python = "/home/denni/.hermes/installs/953423788c16afe2/environments/64008cbe887048c3b0cf1cdfa6767163/venv/bin/python";
    char *script = "/home/denni/trimac_mount_helper.py";
    
    // 準備參數
    char **new_argv = malloc((argc + 3) * sizeof(char *));
    new_argv[0] = python;
    new_argv[1] = script;
    for (int i = 1; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }
    new_argv[argc + 1] = NULL;
    
    // 執行
    execv(python, new_argv);
    
    // 如果 execv 返回說明失敗
    perror("execv failed");
    return 1;
}