# core/presence.py
#
# Her "now": what the top bar should say she's up to.
# 她的「当下」——顶栏那句状态该说什么。
# Two paths, because weather needs a network call: activity_text()
# is instant and safe on the UI thread, full_text() is not.
# 天气要发网络请求，所以拆成快慢两条路：activity_text() 秒出、
# 界面线程随便调；full_text() 会联网，只能丢给子线程。
#
# Show her activity first, append the weather when it lands; the
# reverse order would freeze the UI for ten-odd seconds.
# 先显示她在做什么，天气查到再补上；反过来网络一慢会卡十几秒。

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
