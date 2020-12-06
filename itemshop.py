import json
import logging
from math import ceil
from sys import exit
from time import sleep
from datetime import date

import coloredlogs
import twitter
from PIL import Image, ImageDraw

from util import ImageUtil, Utility

log = logging.getLogger(__name__)
coloredlogs.install(
    level="INFO", fmt="[%(asctime)s] %(message)s", datefmt="%I:%M:%S")

today = date.today()

class Athena:
    """Fortnite Item Shop Generator."""

    def main(self):
        print("Athena - Fortnite Item Shop Generator")
        print("https://github.com/Liimiitz/Athena\n")

        initialized = Athena.LoadConfiguration(self)

        if initialized is True:
            if self.delay > 0:
                log.info(f"Delaying process start for {self.delay}s...")
                sleep(self.delay)

            itemShop = Utility.GET(
                self,
                "https://fortniteapi.io/v1/shop",
                {"Authorization": self.apiKey},
                {"lang": self.language},
            )

            if itemShop is not None:
                itemShop = json.loads(itemShop)

                # Strip time from the timestamp, we only need the date
                date = Utility.ISOtoHuman(self, today, self.language)
                log.info(f"Retrieved Item Shop for {date}")

                shopImage = Athena.GenerateImage(self, date, itemShop)

                if shopImage is True:
                    if self.twitterEnabled is True:
                        Athena.Tweet(self, date)

    def LoadConfiguration(self):
        """
        Set the configuration values specified in configuration.json

        Return True if configuration sucessfully loaded.
        """

        configuration = json.loads(
            Utility.ReadFile(self, "configuration", "json"))

        try:
            self.delay = configuration["delayStart"]
            self.apiKey = configuration["fortniteAPI"]["apiKey"]
            self.language = configuration["language"]
            self.supportACreator = configuration["supportACreator"]
            self.twitterEnabled = configuration["twitter"]["enabled"]
            self.twitterAPIKey = configuration["twitter"]["apiKey"]
            self.twitterAPISecret = configuration["twitter"]["apiSecret"]
            self.twitterAccessToken = configuration["twitter"]["accessToken"]
            self.twitterAccessSecret = configuration["twitter"]["accessSecret"]

            log.info("Loaded configuration")

            return True
        except Exception as e:
            log.critical(f"Failed to load configuration, {e}")

    def GenerateImage(self, date: str, itemShop: dict):
        """
        Generate the Item Shop image using the provided Item Shop.

        Return True if image sucessfully saved.
        """

        try:
            featured = itemShop["featured"] + itemShop["specialFeatured"]
            daily = itemShop["daily"] + itemShop["specialDaily"]

            log.info(f"Featured: {len(featured)}, Daily: {len(daily)}")

            if (len(featured) >= 1):
                rowsDaily = 3
                rowsFeatured = 3
                width = ((340 * 6) + 10)
                height = max(ceil(len(featured) / 3), ceil(len(daily) / 3))
                dailyStartX = 1055

            if (len(featured) >= 21):
                rowsDaily = 3
                rowsFeatured = 6
                width = ((340 * 9) + 10)
                height = max(ceil(len(featured) / 6), ceil(len(daily) / 6))
                dailyStartX = 2075

            if (len(featured) >= 21) and (len(daily) >= 21):
                rowsDaily = 6
                rowsFeatured = 6
                width = ((340 * 12) - 25)
                height = max(ceil(len(featured) / 6), ceil(len(daily) / 6))
                dailyStartX = 2075

        except Exception as e:
            log.critical(f"Failed to parse Item Shop Featured and Daily items, {e}")
            return False

        # Determine the max amount of rows required for the current
        # Item Shop when there are 3 columns for both Featured and Daily.
        # This allows us to determine the image height.

        shopImage = Image.new("RGB", (width, (530 * height) + 350))

        try:
            background = ImageUtil.Open(self, "background.png")
            background = ImageUtil.RatioResize(
                self, background, shopImage.width, shopImage.height
            )
            shopImage.paste(
                background, ImageUtil.CenterX(
                    self, background.width, shopImage.width)
            )
        except FileNotFoundError:
            log.warning(
                "Failed to open background.png, defaulting to dark gray")
            shopImage.paste(
                (34, 37, 40), [0, 0, shopImage.size[0], shopImage.size[1]])

        canvas = ImageDraw.Draw(shopImage)
        font = ImageUtil.Font(self, 80)

        textWidth, _ = font.getsize("FORTNITE ITEM SHOP ROTATION")
        canvas.text(ImageUtil.CenterX(self, textWidth, shopImage.width, 30), "FORTNITE ITEM SHOP ROTATION", (255, 255, 255), font=font)
        textWidth, _ = font.getsize(date.upper())
        canvas.text(ImageUtil.CenterX(self, textWidth, shopImage.width, 120), date.upper(), (255, 255, 255), font=font)
        
        canvas.text((20, 240), "FEATURED", (255, 255, 255), font=font, anchor=None, spacing=4, align="left")
        canvas.text((shopImage.width - 230, 240), "DAILY", (255, 255, 255), font=font, anchor=None, spacing=4, align="right")

        # Track grid position
        i = 0

        for item in featured:
            card = Athena.GenerateCard(self, item)

            if card is not None:
                shopImage.paste(
                    card,
                    (
                        (20 + ((i % rowsFeatured) * (310 + 20))),
                        (350 + ((i // rowsFeatured) * (510 + 20))),
                    ),
                    card,
                )

                i += 1

        # Reset grid position
        i = 0

        for item in daily:
            card = Athena.GenerateCard(self, item)

            if card is not None:
                shopImage.paste(
                    card,
                    (
                        (dailyStartX + ((i % rowsDaily) * (310 + 20))),
                        (350 + ((i // rowsDaily) * (510 + 20))),
                    ),
                    card,
                )

                i += 1

        try:
            shopImage.save("itemshop.jpeg", optimize=True,quality=85)
            if(itemShop["fullShop"] == False):
             log.info("Some cosmetics are missing from this shop!")
            log.info("Generated Item Shop image")

            return True
        except Exception as e:
            log.critical(f"Failed to save Item Shop image, {e}")

    def GenerateCard(self, item: dict):
        """Return the card image for the provided Fortnite Item Shop item."""

        try:
            name = item["name"].lower()
            rarity = item["rarity"].lower()
            category = item["type"].lower()
            price = item["price"]


            if (item["image"]):
                icon = item["image"]
            else:
                icon = item["icon"]

        except Exception as e:
            log.error(f"Failed to parse item {name}, {e}")

            return

        if rarity == "frozen series":
            blendColor = (148, 223, 255)
            rarity = "Frozen"
        elif rarity == "lava series":
            blendColor = (234, 141, 35)
            rarity = "Lava"
        elif rarity == "legendary":
            blendColor = (211, 120, 65)
            rarity = "Legendary"
        elif rarity == "slurp series":
            blendColor = (0, 233, 176)
            rarity = "Slurp"
        elif rarity == "dark":
            blendColor = (251, 34, 223)
            rarity = "Dark"
        elif rarity == "star wars series":
            blendColor = (231, 196, 19)
            rarity = "Star Wars"
        elif rarity == "marvel":
            blendColor = (197, 51, 52)
            rarity = "Marvel"
        elif rarity == "dc":
            blendColor = (84, 117, 199)
            rarity = "DC"
        elif rarity == "icon series":
            blendColor = (54, 183, 183)
            rarity = "Icon"
        elif rarity == "shadow series":
            blendColor = (113, 113, 113)
            rarity = "Shadow"
        elif rarity == "platform series":
            blendColor = (117,108,235)
            rarity = "Gaming Legends"
        elif rarity == "epic":
            blendColor = (177, 91, 226)
            rarity = "Epic"
        elif rarity == "rare":
            blendColor = (73, 172, 242)
            rarity = "Rare"
        elif rarity == "uncommon":
            blendColor = (96, 170, 58)
            rarity = "Uncommon"
        elif rarity == "common":
            blendColor = (190, 190, 190)
            rarity = "Common"
        else:
            blendColor = (255, 255, 255)
            rarity = "Unknown"

        card = Image.new("RGBA", (310, 510))

        try:
            layer = ImageUtil.Open(
                self, f"./shopTemplates/{rarity.capitalize()}BG.png")
        except FileNotFoundError:
            log.warn(
                f"Failed to open {rarity.capitalize()}BG.png, defaulted to Common")
            layer = ImageUtil.Open(self, "./shopTemplates/CommonBG.png")
        card.paste(layer)

        icon = ImageUtil.Download(self, icon)
        if (category == "outfit") or (category == "emote"):
            icon = ImageUtil.RatioResize(self, icon, 285, 365)
        elif category == "wrap":
            icon = ImageUtil.RatioResize(self, icon, 230, 310)
        else:
            icon = ImageUtil.RatioResize(self, icon, 310, 390)
        if (category == "outfit") or (category == "emote"):
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width), icon)
        else:
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), icon)

        try:
            layer = ImageUtil.Open(
                self, f"./shopTemplates/{rarity.capitalize()}OV.png")
        except FileNotFoundError:
            log.warn(
                f"Failed to open {rarity.capitalize()}OV.png, defaulted to Common")
            layer = ImageUtil.Open(self, "./shopTemplates/CommonOV.png")

        card.paste(layer, layer)

        canvas = ImageDraw.Draw(card)

        vbucks = ImageUtil.Open(self, "vbucks.png")
        vbucks = ImageUtil.RatioResize(self, vbucks, 40, 40)

        font = ImageUtil.Font(self, 40)
        price = str(f"{price:,}")
        textWidth, _ = font.getsize(price)

        canvas.text(ImageUtil.CenterX(self, ((textWidth - 5) - vbucks.width), card.width, 347), price, (255, 255, 255), font=font)
        card.paste(vbucks,ImageUtil.CenterX(self, (vbucks.width + (textWidth + 5)), card.width, 350),vbucks)

        font = ImageUtil.Font(self, 40)
        itemName = name.upper().replace(" OUTFIT", "").replace(" PICKAXE", "").replace(" BUNDLE", "")

        if(category == "bundle"):
            itemName = name.upper().replace(" BUNDLE", "")

        textWidth, _ = font.getsize(itemName)

        change = 0
        if textWidth >= 270:
            # Ensure that the item name does not overflow
            font, textWidth, change = ImageUtil.FitTextX(self, itemName, 40, 250)
        canvas.text(ImageUtil.CenterX(self, textWidth, card.width, (400 + (change / 2))), itemName, (255, 255, 255), font=font)
      
        font = ImageUtil.Font(self, 40)
        textWidth, _ = font.getsize(f"{rarity.upper()} {category.upper()}")
        
        change = 0
        if textWidth >= 270:
            # Ensure that the item rarity/type does not overflow
            font, textWidth, change = ImageUtil.FitTextX(self, f"{rarity.upper()} {category.upper()}", 30, 250)
        canvas.text(ImageUtil.CenterX(self, textWidth, card.width, (450 + (change / 2))), f"{rarity.upper()} {category.upper()}", blendColor, font=font)
        return card

    def Tweet(self, date: str):
        """
        Tweet the current `Item Shop` image to Twitter using the credentials provided
        in `configuration.json`.
        """

        try:
            twitterAPI = twitter.Api(
                consumer_key=self.twitterAPIKey,
                consumer_secret=self.twitterAPISecret,
                access_token_key=self.twitterAccessToken,
                access_token_secret=self.twitterAccessSecret,
            )

            twitterAPI.VerifyCredentials()

        except Exception as e:
            log.critical(f"Failed to authenticate with Twitter, {e}")

            return

        body = f"Battle Royale - #Fortnite Item Shop | {date}"

        if self.supportACreator is not None:
            body = f"{body}\n\nUse code: {self.supportACreator} in the item shop!"

        try:

            with open("itemshop.jpeg", "rb") as shopImage:
                twitterAPI.PostUpdate(body, media=shopImage)

            log.info("Tweeted Item Shop")
        except Exception as e:
            log.critical(f"Failed to Tweet Item Shop, {e}")

if __name__ == "__main__":
    try:
        Athena.main(Athena)
    except KeyboardInterrupt:
        log.info("Exiting...")
        exit()