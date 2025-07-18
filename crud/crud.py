from fastapi import HTTPException
from fastapi.responses import JSONResponse


class CRUD:
    allowable_tables = ["quizzes"]

    def __init__(self, connect_database, table_name):
        self.connect_database = connect_database
        self.table_name = table_name

        if self.table_name not in self.allowable_tables:
            raise HTTPException(status_code=404, detail="Invalid Table")

    def create_method(self, user_data):
        connection = self.connect_database()
        cursor = connection.cursor()

        try:
            user_data = dict(user_data)

            columns = ",".join(user_data.keys())
            placeholders = ",".join(["%s"] * len(user_data))
            values = tuple(user_data.values())

            query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING id"
            cursor.execute(query, values)
            connection.commit()
            fetched_id = cursor.fetchone()

            if not fetched_id:
                raise HTTPException(status_code=500, detail="Something Went Wrong")

            return JSONResponse(
                content={"message": "Data is Inserted", "id": fetched_id[0]}
            )

        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            cursor.close()
            connection.close()

    def read_method(self):
        connection = self.connect_database()
        cursor = connection.cursor()

        try:
            query = f"SELECT * FROM {self.table_name}"
            cursor.execute(query)
            all_data = cursor.fetchall()

            if not all_data:
                raise HTTPException(status_code=404, detail="No data found")

            return all_data

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        finally:
            cursor.close()
            connection.close()

    def read_method_each(self, id: str):
        connection = self.connect_database()
        cursor = connection.cursor()

        try:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id=%s", (id,))
            fetched_data = cursor.fetchone()

            if not fetched_data:
                raise HTTPException(status_code=404, detail="No Data Found")

            return fetched_data

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

        finally:
            cursor.close()
            connection.close()

    def update_method(self, update_data, condition_name: str, condition_value):
        connection = self.connect_database()
        cursor = connection.cursor()

        try:
            update_data = dict(update_data)
            changes_data = ",".join([f"{key}=%s" for key in update_data.keys()])

            values_list = list(update_data.values())
            values_list.append(condition_value)

            query = f"UPDATE {self.table_name} SET {changes_data} WHERE {condition_name}=%s RETURNING id"
            cursor.execute(query, tuple(values_list))
            returned_data = cursor.fetchone()

            if not returned_data:
                raise HTTPException(
                    status_code=404, detail="No matching record to update"
                )

            connection.commit()

            return JSONResponse(
                content={"message": "Data Updated Successfully", "id": returned_data[0]}
            )

        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            cursor.close()
            connection.close()

    def delete_method(self, condition_name: str, condition_value):
        connection = self.connect_database()
        cursor = connection.cursor()

        try:
            query = f"DELETE FROM {self.table_name} WHERE {condition_name}=%s"
            cursor.execute(query, (condition_value,))
            connection.commit()

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="No data found to delete")

            return JSONResponse(content={"message": "Data is Deleted"})

        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=str(e))

        finally:
            cursor.close()
            connection.close()
