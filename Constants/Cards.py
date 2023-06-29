playerSets = {
    # only for testing purposes
    3: {
        "roles": [
            "Либерал",
            "Фашист",
            "Гитлер"
        ],
        "track": [
            None,
            None,
            "policy",
            "kill",
            "kill",
            "win"
        ]
    },
    # only for testing purposes
    4: {
        "roles": [
            *["Либерал"]*2,
            "Фашист",
            "Гитлер"
        ],
        "track": [
            None,
            None,
            "policy",
            "kill",
            "kill",
            "win"
        ]
    },
    5: {
        "roles": [
            *["Либерал"]*3,
            "Фашист",
            "Гитлер"
        ],
        "track": [
            None,
            None,
            "policy",
            "kill",
            "kill",
            "win"
        ]
    },
    6: {
        "roles": [
            *["Либерал"]*4,
            "Фашист",
            "Гитлер"
        ],
        "track": [
            None,
            None,
            "policy",
            "kill",
            "kill",
            "win"
        ]
    },
    7: {
        "roles": [
            *["Либерал"]*4,
            *["Фашист"]*2,
            "Гитлер"
        ],
        "track": [
            None,
            "inspect",
            "choose",
            "kill",
            "kill",
            "win"
        ]
    },
    8: {
        "roles": [
            *["Либерал"]*5,
            *["Фашист"]*2,
            "Гитлер"
        ],
        "track": [
            None,
            "inspect",
            "choose",
            "kill",
            "kill",
            "win"
        ]
    },
    9: {
        "roles": [
            *["Либерал"]*5,
            *["Фашист"]*3,
            "Гитлер"
        ],
        "track": [
            "inspect",
            "inspect",
            "choose",
            "kill",
            "kill",
            "win"
        ]
    },
    10: {
        "roles": [
            *["Либерал"]*6,
            *["Фашист"]*3,
            "Гитлер"
        ],
        "track": [
            "inspect",
            "inspect",
            "choose",
            "kill",
            "kill",
            "win"
        ]
    },
}

policies = ["либеральный"]*6 + ["фашистский"]*11