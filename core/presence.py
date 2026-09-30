# core/presence.py
#
# 她的「当下」——顶栏那句状态该说什么。
#
# 拆成快慢两条路，是因为天气要发网络请求：
#   activity_text() 秒出，界面线程随便调
#   full_text()     会联网，只能丢给子线程
#
# 顶栏先立刻显示她在做什么，
# 天气查到了再补上去。
# 反过来做的话，网络一慢
# 整个界面会卡住十几秒。

from core.activity import ActivityEngine

from core.identity import Identity


def activity_text():

    occupation = (
        Identity().get("occupation") or ""
    )

    return ActivityEngine().current(
        occupation
    )


def weather_text():

    """
    会发网络请求。
    不要在界面线程里调这个。
    """

    from core.weather import get_weather


    city = (
        Identity().get("current_city") or ""
    ).strip()


    if not city:

        return None


    data = get_weather(city)


    if not data:

        return None


    weather = data.get("weather") or ""

    temp = data.get("temperature")


    if temp is None:

        return None


    return f"{weather} {round(temp)}°"


def full_text():

    """
    她在做什么 · 她那边的天气。
    会发网络请求，只能在子线程里调。
    """

    text = activity_text()

    weather = weather_text()


    if weather:

        text = f"{text} · {weather}"


    return text
