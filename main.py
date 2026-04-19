from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from db import get_connection
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import sqlite3


app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "pong"}

class FilmResponse(BaseModel):
    ID: int | None = None
    Nom: str
    Note: float | None = None
    DateSortie: int
    Image: str | None = None
    Video: str | None = None
    Genre_ID: int | None = None

@app.post("/film")
async def createFilm(film : FilmResponse):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO Film (Nom,Note,DateSortie,Image,Video) VALUES('{film.nom}',{film.note},{film.dateSortie},'{film.image}','{film.video}') RETURNING *
            """)
        res = cursor.fetchone()
        print(res)
        return res


class PaginatedResponse(BaseModel):
    data: list[FilmResponse]
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
        cursor.execute(f"SELECT * FROM Film {condition} ORDER BY DateSortie desc LIMIT ? OFFSET ? ", params)
        res = cursor.fetchall()
        data = [dict(resultat) for resultat in res]


    return {"data": data , "page": page, "per_page": per_page, "total": nb_total_films}


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



@app.get("/films/{film_id}", response_model=FilmResponse)
def get_film_by_id(film_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Film WHERE ID = ?", (film_id,))
        res = cursor.fetchone()
        if res is None:
            raise HTTPException(status_code=404, detail="Film non trouvé")
        return dict(res)



class UserRegister(BaseModel):
    email: str
    pseudo: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24) #on a accès une journée
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode,"cle_secrete_longue_pour_netflix_mines_2026", algorithm="HS256")
    return encoded_jwt

#avant de rajouter register, il faut qu'on hache les mots de passe pour ne pas les stocker en clair

def hash_pwd(password: str):
    bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(bytes, salt).decode('utf-8') #parce qu'on veut stocker du texte

@app.post("/auth/register", response_model=TokenResponse)
def register(user: UserRegister):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Utilisateur WHERE AdresseMail = ?", (user.email,))
        
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Cet email est déjà pris.")
        
        cursor.execute("SELECT ID FROM Utilisateur WHERE Pseudo = ?", (user.pseudo,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ce pseudo est déjà pris.")
        
        cursor.execute("""
                       INSERT INTO Utilisateur (AdresseMail, Pseudo, MotDePasse) VALUES (?, ?, ?)
                       """,
                       (user.email, user.pseudo, hash_pwd(user.password)))
        
        user_id = cursor.lastrowid
    
    token = create_access_token(data={"user_id": str(user_id)})
    return TokenResponse(access_token=token, token_type="bearer")

#il nous faut une fonction pour vérifier que le hash stocké correspond bien au mdp renseigné
def verify_pwd(original_password: str, hashed_password: str):
    password_byte = original_password.encode('utf-8')
    hashed_password_byte = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte, hashed_password_byte)


class UserLogin(BaseModel):
    email : str
    password: str

@app.post("/auth/login", response_model=TokenResponse)
def login(user: UserLogin):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID, MotDePasse FROM Utilisateur WHERE AdresseMail = ?", (user.email,))
        db_user = cursor.fetchone()
        
        if db_user is None:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect") # on ne dit pas juste que l'email n'existe pas par sécurité sinon qqun de malveillant pourrait juste faire plein de requêtes pour savoir quelles adresses sont dans notre base de données
       
        user_id = db_user["ID"]
        hashed_password = db_user["MotDePasse"]
        if not verify_pwd(user.password, hashed_password):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
            
    token = create_access_token(data={"user_id": user_id})
    
    return TokenResponse(access_token=token, token_type="bearer")

security = HTTPBearer()
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, "cle_secrete_longue_pour_netflix_mines_2026", algorithms=["HS256"]) # on prend le token et on le check en utiliant notre clé super secrète
        user_id = payload.get("user_id")
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré: reconnectez-vous")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token bidon")
    

class PreferenceRequest(BaseModel):
    genre_id: int

@app.post("/preferences", status_code=201)
def add_preference(preference: PreferenceRequest, user_id: str = Depends(get_current_user)): #on vérifie qu'on est connecté
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Genre WHERE ID = ?", (preference.genre_id,))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Genre inexistant")
        
        try:
            cursor.execute("""
                INSERT INTO Genre_Utilisateur (ID_Genre, ID_User) VALUES (?, ?)
                """, 
                (preference.genre_id, int(user_id)) 
            )
        except sqlite3.IntegrityError: #on veut pas de doublons, ça plante si y'en a un cf. schema.sql
            raise HTTPException(status_code=409, detail="Ce genre est déjà dans vos favoris")
            
    return {"message": "Genre ajouté aux favoris"}



@app.delete("/preferences/{genre_id}")
def remove_preference(genre_id: int, user_id: str = Depends(get_current_user)):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM Genre_Utilisateur WHERE ID_Genre = ? AND ID_User = ?
            """, 
            (genre_id, int(user_id))
        )

        if cursor.rowcount == 0: # ça nous dit combien de lignes ont été effacées
            raise HTTPException(status_code=404, detail="Ce genre n'est pas dans vos favoris")
            
    return {"message": "Genre retiré des favoris"}


@app.get("/preferences/recommendations", response_model=list[FilmResponse])
def get_recommendations(user_id: str = Depends(get_current_user)):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Film.* FROM Film
            JOIN Genre_Utilisateur ON Film.Genre_ID = Genre_Utilisateur.ID_Genre 
            WHERE Genre_Utilisateur.ID_User = ?
            ORDER BY Film.DateSortie DESC  
            LIMIT 5
            """, 
            (int(user_id),)
        )
        # en gros on a fait quoi ? 
        # on colle la table Film à la table genre_utilisateur en faisant correspondre genre_id de film et id_genre des favoris
        # on filtre pour garder que notre utilisateur
        # on veut des recommandations triées par date décroissante
        
        res = cursor.fetchall()
        data = [dict(row) for row in res]
    return data




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
