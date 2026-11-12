from dataclasses import dataclass


@dataclass
class Meta:
    slug: str
    title: str
    emoji: str
    ready: bool = False


ALL = [
    Meta("kino", "Kino bot", "film", True),
    Meta("anime", "Anime bot", "anime", True),
    Meta("saver", "Saver bot", "save", True),
    Meta("hashtag", "Hashtag bot", "tag", True),
    Meta("musiqa", "Musiqa bot", "star"),
    Meta("konkurs", "Konkurs bot", "gift"),
    Meta("autohabar", "Autohabar bot", "send"),
    Meta("majburiy", "Majburiy obuna bot", "lock"),
    Meta("pulish", "Pul ishlash bot", "money"),
    Meta("stt", "Ovozni matnga aylantiruvchi bot", "video"),
    Meta("support", "Fikr-mulohaza (support) bot", "user"),
    Meta("dokon", "Do'kon/buyurtma bot", "shop"),
    Meta("pullik", "Pullik kanal bot", "money"),
    Meta("moderator", "Guruh moderator bot", "gear"),
    Meta("rejalash", "Post rejalashtiruvchi bot", "time"),
    Meta("referal", "Referal (taklif) bot", "link"),
    Meta("bron", "Yozilish (bron) bot", "time"),
    Meta("anketa", "Anketa/ariza bot", "check"),
    Meta("ovoz", "Ovoz berish bot", "stat"),
    Meta("ombor", "Kitob/fayl ombori bot", "save"),
]
BY_SLUG = {m.slug: m for m in ALL}
