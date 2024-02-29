CTFd._internal.challenge.data = undefined

CTFd._internal.challenge.renderer = null;


CTFd._internal.challenge.preRender = function() {}

CTFd._internal.challenge.render = null;


CTFd._internal.challenge.postRender = function() {}


CTFd._internal.challenge.submit = function(preview) {
    let challenge_id = parseInt(CTFd.lib.$('#challenge-id').val())
    let submission = CTFd.lib.$('#challenge-input').val()

    let body = {
        challenge_id: challenge_id,
        submission: submission,
    };
    let params = {}
    if (preview) {
        params['preview'] = true
    }

    return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
        if (response.status === 429) {
            // User was rate-limited but process response
            return response
        }
        if (response.status === 403) {
            // User is not logged in or CTF is paused.
            return response
        }
        return response
    })
};

function get_docker_status(container, challenge_id) {
    fetch("/api/v1/docker_status")
        .then(function(response) {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error("Network response was not ok");
            }
        })
        .then(function(result) {
            let dockerContainer = document.getElementById('docker_container');
            result['data'].forEach(function(item) {
                if (item.challenge_id == challenge_id && item.docker_image == container) {
                    let ports = String(item.ports).split(',');
                    let data = '';
                    ports.forEach(function(port) {
                        port = String(port);
                        data = data + 'Host: ' + item.host + ' Port: ' + port + '<br />';
                    });
                    dockerContainer.innerHTML = '<pre>Docker Container Information:<br />' + data + '<div class="mt-2" id="' + String(item.instance_id).substring(0, 10) + '_revert_container"></div>';
                    let countDownDate = new Date(parseInt(item.revert_time) * 1000).getTime();
                    let x = setInterval(function() {
                        let now = new Date().getTime();
                        let distance = countDownDate - now;
                        let minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                        let seconds = Math.floor((distance % (1000 * 60)) / 1000);
                        if (seconds < 10) {
                            seconds = "0" + seconds;
                        }
                        document.getElementById(String(item.instance_id).substring(0, 10) + "_revert_container").innerHTML = 'Next Revert Available in ' + minutes + ':' + seconds;
                        if (distance < 0) {
                            clearInterval(x);
                            document.getElementById(String(item.instance_id).substring(0, 10) + "_revert_container").innerHTML = '<a onclick="start_container(\'' + container + '\',\'' + challenge_id + '\');" class=\'btn btn-dark\'><small style=\'color:white;\'><i class="fas fa-redo"></i> Revert</small></a>';
                        }
                    }, 1000);
                    return false;
                }
            });
        })
        .catch(function(error) {
            // Handle error
        });
}


function start_container(container, challenge_id) {
    let dockerContainer = document.getElementById('docker_container');
    dockerContainer.innerHTML = '<div class="text-center"><i class="fas fa-circle-notch fa-spin fa-1x"></i></div>';

    fetch("/api/v1/container?id=" + challenge_id)
        .then(function(response) {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error("Network response was not ok");
            }
        })
        .then(function(result) {
            get_docker_status(container, challenge_id);
        })
        .catch(function(error) {
            ezal({
                title: "Attention!",
                body: "You can only revert a container once per 5 minutes! Please be patient.",
                button: "Got it!"
            });
            get_docker_status(container, challenge_id);
        });
}

var modal =
    '<div class="modal fade" tabindex="-1" role="dialog">' +
    '  <div class="modal-dialog" role="document">' +
    '    <div class="modal-content">' +
    '      <div class="modal-header">' +
    '        <h5 class="modal-title">{0}</h5>' +
    '        <button type="button" class="close" data-dismiss="modal" aria-label="Close">' +
    '          <span aria-hidden="true">&times;</span>' +
    "        </button>" +
    "      </div>" +
    '      <div class="modal-body">' +
    "        <p>{1}</p>" +
    "      </div>" +
    '      <div class="modal-footer">' +
    "      </div>" +
    "    </div>" +
    "  </div>" +
    "</div>";

    function ezal(args) {
        // Create modal HTML
        let modalHtml = modal.replace('{0}', args.title).replace('{1}', args.body);
        let modalElement = document.createElement('div');
        modalElement.innerHTML = modalHtml;
        modalElement.classList.add('custom-modal'); // Add class for styling
    
        // Add button HTML
        let buttonHtml = '<button type="button" class="btn btn-primary custom-modal-close">' + args.button + '</button>';
        let modalFooter = modalElement.querySelector(".modal-footer");
        modalFooter.innerHTML = buttonHtml;
    
        // Append modal to the main element
        document.querySelector("main").appendChild(modalElement);
    
        // Function to show modal
        function showModal() {
            modalElement.style.display = 'block';
        }
    
        // Function to hide modal
        function hideModal() {
            modalElement.style.display = 'none';
            modalElement.remove(); // Remove element after hiding
        }
    
        // Show the modal
        showModal();
    
        // Event listener for closing modal
        modalElement.querySelector('.custom-modal-close').addEventListener('click', hideModal);
    
        // Optional: Click outside the modal content to close
        window.onclick = function(event) {
            if (event.target === modalElement) {
                hideModal();
            }
        };
    
        return modalElement;
    }
    
