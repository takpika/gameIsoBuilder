#!/bin/bash

# 解像度を設定したい値に置き換えてください
desired_resolution="{{RESOLUTION}}"

# 接続されているディスプレイの名前を検出
connected_displays=$(xrandr | grep ' connected' | awk '{ print $1 }')

# 各ディスプレイに対して解像度を設定
for display in $connected_displays; do
    echo "Setting resolution to $desired_resolution on $display"
    xrandr --output $display --mode $desired_resolution
done
