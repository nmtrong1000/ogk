CATALOG = {
    "education": """
        khanacademy.org coursera.org edx.org openstax.org wikipedia.org wiktionary.org britannica.com
        nationalgeographic.org nasa.gov noaa.gov usgs.gov smithsonianmag.com pbs.org ted.com duolingo.com
        codecademy.com freecodecamp.org w3schools.com stackoverflow.com mathsisfun.com wolframalpha.com
        scholastic.com education.com ducksters.com history.com science.org nature.com kids.nationalgeographic.com
        oxfordlearnersdictionaries.com dictionary.cambridge.org gutenberg.org archive.org arxiv.org phet.colorado.edu
        code.org scratch.mit.edu learning.com sciencebuddies.org
    """,
    "entertainment": """
        youtube.com netflix.com disneyplus.com spotify.com soundcloud.com imdb.com rottentomatoes.com twitch.tv
        vimeo.com crunchyroll.com primevideo.com hbomax.com max.com peacocktv.com paramountplus.com
        discoveryplus.com iheart.com pandora.com bandcamp.com last.fm genius.com fandom.com ign.com gamespot.com
        polygon.com variety.com billboard.com rollingstone.com bbc.com cbs.com nbc.com abc.com fox.com
    """,
    "social": """
        facebook.com instagram.com tiktok.com snapchat.com pinterest.com reddit.com x.com twitter.com threads.net
        linkedin.com tumblr.com discord.com telegram.org whatsapp.com messenger.com wechat.com vk.com
        mastodon.social bluesky.app medium.com quora.com meetup.com nextdoor.com bereal.com weibo.com line.me
        signal.org flickr.com producthunt.com
    """,
    "games": """
        roblox.com minecraft.net minecraft.com epicgames.com steampowered.com store.steampowered.com playstation.com
        xbox.com nintendo.com ea.com ubisoft.com riotgames.com leagueoflegends.com valorant.com blizzard.com
        battle.net activision.com mojang.com itch.io gog.com humblebundle.com chess.com lichess.org miniclip.com
        poki.com crazygames.com coolmathgames.com kongregate.com friv.com agar.io slither.io among.us supercell.com
        king.com zynga.com
    """,
    "adult": """
        adultfriendfinder.com onlyfans.com pornhub.com xvideos.com xnxx.com xhamster.com redtube.com youporn.com
        tube8.com spankbang.com chaturbate.com stripchat.com livejasmin.com cam4.com bongacams.com brazzers.com
        realitykings.com naughtyamerica.com bangbros.com penthouse.com playboy.com literotica.com lushstories.com
        manyvids.com fansly.com faphouse.com erome.com motherless.com xfreehd.com youjizz.com hclips.com
        thumbzilla.com tnaflix.com yespornplease.com
    """,
    "unclassified": """
        example.com example.org example.net iana.org icann.org cloudflare.com google.com microsoft.com apple.com
        amazon.com yahoo.com duckduckgo.com bing.com startpage.com brave.com mozilla.org opera.com samsung.com
        lenovo.com dell.com hp.com intel.com amd.com nvidia.com github.com gitlab.com bitbucket.org sourceforge.net
        npmjs.com pypi.org crates.io docker.com
    """,
}


def catalog_rows() -> list[tuple[str, str]]:
    rows = {}
    for category, names in CATALOG.items():
        for domain in names.split():
            rows.setdefault(domain.lower(), category)
    return sorted(rows.items())
