import sys
import os
sys.path.insert(0, '/home/bilal/Desktop/week3/scrapy_django_project/web')

import django
os.environ["DJANGO_SETTINGS_MODULE"] = 'web.settings'
django.setup()

from article_api.models import Article, Author, Category

import scrapy
from scrapy.utils.response import open_in_browser

from w3lib.html import remove_tags, replace_escape_chars, replace_tags

"""
TODO
Category Name   - Digital Data  -   Link Collection -   Data Extraction
1. Travel       -   True        -   Done            -   Done
2. News         -   False       -   Not Done        -   Done
3. Capital      -   True        -   Done            -   Done
4. Arts         -   False       -   Not Done                                HTML data in response to ajax request
5. Sport        -   False       -   Not Done        -   Done
6. Culture      -   True        -   Done            -   Done
7. Weather      -   False       -   Done            -   Done
8. Autos        -   True        -   Done            -   Done
9. Food         -   False       -   Not Done
10. Future      -   True        -   Done            -   Done
11. Earth       -   True        -   Not Good
"""
Author.objects.all().delete()
Category.objects.all().delete()
Article.objects.all().delete()

def get_category(response, link):
    return response.urljoin(link).split("/")[3]

class NewsSpider(scrapy.Spider):
    """
        parse() will parse the main homepage and gets categories link
        and forward it to parse_categories() function

        parse_categories() will parse categories page and gets
        all article link and forward it to parse_article() function.
        It also detects if there are more than one page then it follow
        that page and pass it to parse_categories()

        parse_article() will parse the article page and extract
        article title, article published/last updated date, article body
        and article thumbnail image link.
    """

    name = "news_spider"
    start_urls = ['https://www.bbc.com/']

    def parse(self, response):
        categories_links = response.xpath("//div[@id='orb-footer']//div[@class='orb-footer-primary-links']//ul//li//a/@href").extract()

        for link in categories_links:
            #yield {'link':link}
            yield {'link':link}
            yield response.follow(link, callback=self.parse_categories,
                                  meta={
                                        'follow_next':True,
                                        'url':"{url}{{page_no}}".format(url=link),
                                    }
                                 )
    

    def parse_categories(self, response):
        article_links = []
        if b"itemsPerPage" in response.body:
            url = response.meta['url']
            iterable = []
            if response.meta['follow_next']:
                iterable = range(2, 11)
            
            article_links = response.xpath("//a[h3[@class='promo-unit-title'] and contains(@data-cs-id, 'story-promo-link')]/@href").extract()
            
            for i in iterable:
                yield response.follow(url.format(page_no=i), callback=self.parse_categories,
                                        meta={
                                                'follow_next':False,
                                                'url':url,
                                            }
                                        )
        
        elif response.url == 'https://www.bbc.com/weather':
            article_links = response.xpath("//a[h3[contains(@class, 'title')]]/@href").extract()

        elif response.url == 'https://www.bbc.com/sport':
            article_links = response.xpath("//article//a[span[contains(@class, 'title-text')]]/@href").extract()
        else:
            print("Meow Meow", response.url)

        for link in article_links:
                yield response.follow(link, callback=self.parse_article, meta={'category':get_category(response, link)})

    def parse_article(self, response):
        article_title = ''
        article_author = ''
        article_date = ''
        article_body = ''
        article_category = response.meta['category']
        if article_category in ['travel', 'capital', 'culture', 'autos', 'future']:
            article_body = " ".join(response.xpath("//div[@class='body-content']//p[not(@class) and not(ancestor::blockquote)]/text()").extract())
            #article_body = replace_escape_chars(remove_tags(article_body))
            
            article_title = response.xpath("//h1[@class='primary-heading']/text()").extract_first()
            article_author = response.xpath("//li[contains(@class,'source-attribution-author')]/span/text()").extract_first()
            article_date = response.xpath("//span[contains(@class, 'publication-date')]/text()").extract_first()
        
        elif article_category == 'weather':
            article_body = " ".join(response.xpath("//div[contains(@class, 'feature-body')]/p/text()").extract())
            article_title = response.xpath("//h1[contains(@class, 'header__title')]/text()").extract_first()
            article_date = response.xpath("//span[contains(@class, 'header__duration')]/b/text()").extract_first()

        elif article_category == 'news':
            article_body = " ".join(response.xpath("//div[@property='articleBody']/p/text()").extract())
            article_title = response.xpath("//div[@class='story-body']/h1[@class='story-body__h1']/text()").extract_first()
            article_date = response.xpath("//div[contains(@class, 'date') and ancestor::div[@class='story-body']]/@data-datetime").extract_first()

        elif article_category == 'sport':
            article_body = " ".join(response.xpath("//div[@id='story-body']/p/descendant::text()").extract())
            article_title = response.xpath("//article/h1[contains(@class, 'story-headline')]/text()").extract_first()
            article_date = response.xpath("//div[@class='story-info__list']//time/text()").extract_first()

        Article.objects.abk_insert(article_title, article_category, article_author, article_date, article_body)
        yield {
                    'title': article_title,
                    'body': article_body,
                    'date': article_date,
                    'author': article_author,
                    'category': article_category
            }
