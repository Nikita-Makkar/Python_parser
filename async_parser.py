import os
import re
import xml.etree.ElementTree as ET
import asyncio
import aiohttp
from http import HTTPStatus
from pprint import pprint

from bs4 import BeautifulSoup
from celery import Celery, Task
from dotenv import load_dotenv

load_dotenv()


app = Celery('tender_parser', broker=os.getenv('CELERY_BROKER_URL'))

app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)

SEARCH_URL = f'{os.getenv("BASE_URL")}/epz/order/extendedsearch/results.html'
XML_VIEW_URL = f'{os.getenv("BASE_URL")}/epz/order/notice/printForm/viewXml.html?regNumber={{}}'

headers = {
    "User-Agent": os.getenv("USER_AGENT"),
    "Accept-Encoding": os.getenv("ACCEPT_ENCODING"),
    "Accept": os.getenv("ACCEPT"),
    "Connection": os.getenv("CONNECTION")
}


class FetchLinksTask(Task):
    """
    Задача для асинхронного сбора ссылок XML-формы с конкретной страницы тендера.

        :param page_number: Номер страницы, которую нужно обработать.
        :return: Список ссылок на XML-страницы тендеров.
            """
    async def run(self, page_number):
        params = {"fz44": "on", "pageNumber": page_number}
        async with aiohttp.ClientSession() as session:
            async with session.get(SEARCH_URL, params=params, headers=headers) as response:
                response.raise_for_status()
                text = await response.text()

        soup = BeautifulSoup(text, 'html.parser')
        tender_links = []

        for link in soup.select("a[href*='printForm/view.html?regNumber=']"):
            href = link.get("href")
            reg_number = href.split("regNumber=")[-1]
            xml_link = XML_VIEW_URL.format(reg_number)
            tender_links.append(xml_link)

        return tender_links


class ParseXMLTask(Task):
    """
    Задача для асинхронного парсинга XML-страницы тендера и извлечения даты публикации.

        :param xml_url: URL XML-страницы тендера.
        :return: Дата публикации тендера или None, если данные не найдены.
            """
    async def run(self, xml_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(xml_url, headers=headers) as response:
                if response.status == HTTPStatus.FOUND:
                    print(f'404 Not Found: {xml_url}')
                    return None

                response.raise_for_status()
                text = await response.text()

        try:
            root = ET.fromstring(text)
            for elem in root.iter():
                elem.tag = re.sub(r'\{.*?\}', '', elem.tag)

            publish_date = root.find(".//publishDTInEIS")
            return publish_date.text if publish_date is not None else None

        except ET.ParseError:
            print(f'Ошибка парсинга XML: {xml_url}')
            return None


# Регистрируем таски
app.register_task(FetchLinksTask())
app.register_task(ParseXMLTask())


async def main():
    links_task = FetchLinksTask()
    parse_task = ParseXMLTask()

    all_tender_links = []
    for page in range(1, int(os.getenv("PAGE_NUMBER")) + 1):
        all_tender_links.extend(await links_task.run(page))

    parse_tasks = [parse_task.run(link) for link in all_tender_links]

    results = await asyncio.gather(*parse_tasks)
    results_dict = dict(zip(all_tender_links, results))
    pprint(results_dict)


if __name__ == "__main__":
    asyncio.run(main())
