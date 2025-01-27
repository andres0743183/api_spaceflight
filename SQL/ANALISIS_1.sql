#Calculo de la cantidad de articulos por año
SELECT year,  count(0) FROM "prueba_1"."articles_096e55266a6714af15b7fc85ded7a52a" 
group by year
order by  year desc;

#Calculo de la cantidad de articulos por año y por sitio de noticias
SELECT year, news_site, count(0) FROM "prueba_1"."articles"
group by year, news_site
order by  year desc, news_site;

