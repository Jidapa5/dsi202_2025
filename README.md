# dsi202
# MindVibe - Outfit Rental Application

MindVibe is a web application built with Django that allows users to browse and rent outfits.

## Features

* **Outfit Listing:** Browse available outfits with details like name, description, price, size, and material.
* **Outfit Details:** View detailed information about each outfit.
* **Search:** Search for outfits by name.
* **User Authentication:** Register, log in, and log out.
* **Rental:** Rent outfits for a specified duration.

## User Stories

1.  As a user, I want to be able to register for an account so that I can rent outfits.
2.  As a user, I want to be able to log in to my account so that I can access the rental features.
3.  As a user, I want to be able to browse a list of outfits so that I can find something to rent.
4.  As a user, I want to be able to view the details of an outfit so that I can make an informed decision.
5.  As a user, I want to be able to rent an outfit for a specific duration.

## Installation and Usage

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd dsi202
    ```

2.  **Build and run the Docker container:**

    ```bash
    docker-compose up --build
    ```

3.  **Access the application:**

    Open your web browser and go to `http://localhost:8000`.

4.  **Create a superuser (admin account):**

    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

    Follow the prompts to create an admin user.

## Notes

* This is a basic implementation and can be further enhanced with features like payment integration, user profile management, and more advanced rental options.
* Remember to replace `<repository_url>` with the actual URL of your repository.