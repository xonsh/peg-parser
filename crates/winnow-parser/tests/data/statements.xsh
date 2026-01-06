# function
def get_repo_url():
    raw = $(git remote get-url --push origin).rstrip()
    return raw.replace('https://github.com/', '')
