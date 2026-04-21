系统对接API定义：

驾驶舱座椅件号查询，查询该构型座椅的全部零部件信息
请求方式：get
Url地址：
Http://101.201.101.48/seat/seatpartquery?seatpn=TAAI3-03CE10-01&sb=C,D,E,F

Responses：
{
    "pn": "TAAI3-03CE10-01",
    "sb": "C,D,E,F",
    "partlist": [
        {
            "name": "马达",
            "pn": "4136290006",
             // 如果有关联件或关联辅料
            "child": [
                {
                    "name": "马达下部垫片",
                    "pn": "23351AC080LE"
                },
                {
                    "name": "马达下部垫片",
                    "pn": "23351AC080LE"
                }
            ]
        },
        {
            "name": "靠背前罩",
            "pn": "TAAI3-402030-01"
        }
    ]
}

座椅铭牌识别请求
Url地址：
https://p459329s04.uicp.fun/api/IDPlateDecode/DecodeMatchSeatPlate



