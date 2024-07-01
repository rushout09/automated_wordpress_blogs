# Automated WordPress Blogs
Automatically generate and publish SEO Optimised WordPress blogs with AI (currently works with Yoast SEO).

## Requirements
1. Python 3.8 above
2. OpenAI API keys (First, create an OpenAI account or sign in. Next, navigate to the API key page and "Create new secret key", optionally naming the key. )
3. WordPress Username and Application Password. (Go to your site's wp-admin page. Example: mysite.com/wp-admin -> users -> edit user -> new application password)
![img.png](images/img.png)
4. Install the following plugin: https://github.com/ChazUK/wp-api-yoast-meta (required to add meta description, seo title, etc for yoast seo.)
   1. Download the code from above url as zip.
   2. Go to your site's wp-admin page. Example: mysite.com/wp-admin
   3. Go to plugins -> Add New Plugin -> Upload Plugin -> Choose File -> Select the Zip file downloaded earlier.


## How it works:
1. Clone this Repo, Create and Activate a Virtual Env.
   ```
   git clone git@github.com:rushout09/automated_wordpress_blogs.git
   cd automated_wordpress_blogs
   python3 -m venv venv
   source venv/bin/activate
    ```
2. Install requirements:
    ```
   pip install -r requirements.txt
    ```
3. Rename .env.sample to .env and update the keys
4. Run the main.py file
```python3 main.py```