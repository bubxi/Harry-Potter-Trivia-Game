import psycopg2

def connection():
    conn = psycopg2.connect(database="Harry_Potter_OWLS_Game",
                        host="localhost",
                        user="postgres",
                        password="(d...)",
                        port="5432")

    #cursor() comes from the psycopg2 library
    #allows interaction with the database
    cursor = conn.cursor() #used to fetch rows from result of a query and iterate through them
    return conn, cursor

def execute_query(cursor, query):
    cursor.execute(query) #executes the query being passed in
    query_result = cursor.fetchone()[0] #fetches the results and assigns it to query_result
    return query_result