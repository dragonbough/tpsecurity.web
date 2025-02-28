document.getElementById("post_form").style.display = "none";


function add_post() {
    var form = document.getElementById("post_form")
    var button = document.getElementById("add_post")
    if (form.style.display == 'none') {
        form.style.display = "block";
        button.textContent = "Cancel"
        button.className = "btn btn-outline-danger btn-lg"
      } else {
        form.style.display = "none";
        button.textContent = "Add Post"
        button.className = "btn btn-primary btn-lg"
      }
}

document.getElementById("add_post").addEventListener("click", add_post)
