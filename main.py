from fastapi import FastAPI
from pydantic import BaseModel
from db import get_connection

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "pong"}

class Film(BaseModel):
    ID: int | None = None
    Nom: str
    Note: float | None = None
    DateSortie: int
    Image: str | None = None
    Video: str | None = None
    Genre_ID: int | None = None

@app.post("/film")
async def createFilm(film : Film):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO Film (Nom,Note,DateSortie,Image,Video)  
            VALUES('{film.nom}',{film.note},{film.dateSortie},'{film.image}','{film.video}') RETURNING *
            """)
        res = cursor.fetchone()
        print(res)
        return res


class PaginatedResponse(BaseModel):
    data: list[Film]
    page: int
    per_page: int
    total: int

@app.get("/films", response_model=PaginatedResponse)
def  get_films(page: int = 1, per_page: int = 20, genre_id: int = None):
    with get_connection() as conn:
        cursor = conn.cursor()

        condition = ""
        params=[]

        #Filtrer par genre
        if genre_id is not None:
            condition = "WHERE Genre_ID = ?"
            params.append(genre_id)


        #On calcule le nombre total de film
        cursor.execute(f"SELECT COUNT(*) FROM Film {condition}", params)
        nb_total_films = cursor.fetchone()[0]

        #On affiche tous les films avec la bonne pagination
        offset = (page-1)*per_page
        params.append(per_page)
        params.append(offset)
        cursor.execute(f"SELECT * FROM Film {condition} LIMIT ? OFFSET ?", params)
        res = cursor.fetchall()
        data = [dict(resultat) for resultat in res]


    return {"data": data , "page": page, "per_page": per_page, "total": nb_total_films}

@app.get("/films/{film_id}", response_model=Film)
def get_film_by_id(film_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Film WHERE ID = ?", (film_id,))
        res = cursor.fetchone()
        return dict(res)
    
class GenreResponse(BaseModel):
    ID : int
    Type : str
    
@app.get("/genres", response_model=list[GenreResponse])
def  get_genres():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM Genre ")
        res = cursor.fetchall()
        data = [dict(resultat) for resultat in res]


    return data




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
