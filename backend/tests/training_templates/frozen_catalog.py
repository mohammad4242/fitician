from __future__ import annotations

# Hash literals intentionally stay readable as one value per snapshot row.
# ruff: noqa: E501
import dataclasses
import hashlib
import json
from enum import StrEnum

FROZEN_2_3_4_SIGNATURES = {
    "p01-2-day-full-body-ab-first-month": "f9ca4cdb7211a44db574d5d51ef9de18dadfad4b4e225fa657a3c032e8861718",
    "p02-2-day-full-body-ab-beginner": "5733018d104df5e4f7139b41dce51e79dc0d88b55be217866bdd2a0a35e9a381",
    "p03-2-day-full-body-ab-intermediate": "aff350d429b695e695ef2c6dff41f4792be2d626144fefc5ad4c27cde8a440c4",
    "p04-3-day-upper-lower-full-first-month": "7f91e56fe77fa6f7b859b48bad6fe349cda8de251b6d05660dfb2fcd33854e55",
    "p05-3-day-upper-lower-full-beginner": "96ca9f8f952f57f24936e5d17febc01cc55ec5960df549eecef72172f20f86c4",
    "p06-3-day-upper-lower-full-intermediate": "7532857447eeaf1418e22da927813cf9373af62a779b99a5384c41c7f5fa7783",
    "p07-3-day-upper-lower-full-advanced": "2215024afca36fa49941e8fcaa4b7b1796eb63a4263c21c7d27a958f9d766fdd",
    "p08-3-day-upper-lower-upper-beginner": "3d2ab8ea4d8a81cee34b325670134f6fc97b53c5456a9183b9d506a595f1e4f2",
    "p09-3-day-upper-lower-upper-intermediate": "94e846d66c8f4bbbabe9caeff3c1b3a58376f64626ffb97ac6dd9c351f752fee",
    "p10-3-day-upper-lower-upper-advanced": "4cc1a0ce18152767339b58aa5162d2763366168c7b077789173ff2bf5b630b77",
    "p11-3-day-lower-upper-lower-beginner": "9cb4b0ced2d995d00e75339c3744f25441915b2d22cd6c72d84c13d791f250a6",
    "p12-3-day-lower-upper-lower-intermediate": "a87b8d4f019d9b6d2c5176a483a532134528b25a3b77c771a7aff66a1728cf2c",
    "p13-3-day-lower-upper-lower-advanced": "ed67486efb57457b7eb63d30872d01e36598eb111ed32f2bd007486aa9fd103f",
    "p14-4-day-upper-lower-upper-lower-first-month": "0fea5d0adcb94067d8631c40aeb0190b1982f6a76bea0c5dba239dd18a217da9",
    "p15-4-day-upper-lower-upper-lower-beginner": "0c26cc92fc245800ef2920de65d4272a393646dea80e5efbca5e98e3f485ed91",
    "p16-4-day-upper-lower-upper-lower-intermediate": "ee0d9bccf8c5ff8337c64062c5fb30ee61aed7c98d00662ee8259ab4f808a903",
    "p17-4-day-upper-lower-upper-lower-advanced": "97a9de427e254f75aa6dd938d0f57287e76c4494400060921c32e48299c8b725",
    "p18-4-day-3-upper-1-lower-beginner": "0426398a95d0101c65cf5e7862aa29f9cf3672f4fe4421ae9760ca3be0a5eafa",
    "p19-4-day-3-upper-1-lower-intermediate": "c7a99965c5c89fec34bfce61f9aa3e79f3c6ce22d268cc3623ed6fcea1a2fe6d",
    "p20-4-day-3-upper-1-lower-advanced": "6088732e480e7f94930ddfac7179ded8d784f78d037f5354e24100b9d39b606c",
    "p21-4-day-3-lower-1-upper-beginner": "d5643af55bc73c1d2da5e24c8a20a3d500faf89881d025dcc78c896ccab52fd9",
    "p22-4-day-3-lower-1-upper-intermediate": "1a247dd573dedeeb1267f04064b8b23fdd16f17c6c2a4f3155c585cc2587e61f",
    "p23-4-day-3-lower-1-upper-advanced": "09642b5a5ee910d674a26858d5bfc5536ecb7a5fdf1c644f566b3ef7cd0f49ed",
    "p24-4-day-push-pull-quads-posterior-intermediate": "f8786842397752aa4af0c4ec92d08b3dc9a7dff2d4898d4894465ac66c608ed6",
    "p25-4-day-push-pull-quads-posterior-advanced": "7a53758d94814f739a84283dcc144c1a1f9c0b88a44ad9775fd2c259abfb771f",
}


def seed_signature(seed: object) -> str:
    def normalize(value: object) -> object:
        if isinstance(value, StrEnum):
            return value.value
        if dataclasses.is_dataclass(value):
            return {
                field.name: normalize(getattr(value, field.name))
                for field in dataclasses.fields(value)
            }
        if isinstance(value, dict):
            return {str(key): normalize(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [normalize(item) for item in value]
        return value

    payload = json.dumps(normalize(seed), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
