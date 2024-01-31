FROM mono:6.12

RUN apt-get update \
    && apt-get install -y autoconf m4 perl tar wget git curl python3 iputils-ping xsel xclip vim python3-pip gnupg2 build-essential libssl-dev sed zlib1g-dev fzf git \
    libbz2-dev libreadline-dev libsqlite3-dev \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev libcanberra-gtk-module make libevent-dev ncurses-dev build-essential bison pkg-config libcanberra-gtk3-module \
    && apt-get upgrade -y 

WORKDIR /root

COPY . /root

RUN mkdir /shared

RUN echo "Installing .NET Core 7.0" \
    && ./helpers/dotnet-install.sh --channel 7.0

WORKDIR /root
ENV HOME=/root

RUN wget http://ftp.gnu.org/gnu/automake/automake-1.15.tar.gz \
    && tar xzf automake-1.15.tar.gz \
    && cd automake-1.15 \
    && ./configure \
    && make \
    && make install

RUN wget https://github.com/tmux/tmux/releases/download/3.3a/tmux-3.3a.tar.gz \
    && tar xzf tmux-3.3a.tar.gz \
    && rm tmux-3.3a.tar.gz

RUN cd tmux-*/ \
    && ./configure \
    && make && make install

RUN echo "Installing Python dependencies" \
    && python3 helpers/get-pip.py \
    && pip install -r requirements.txt

RUN echo "Running msfinstall" \
    && ./helpers/msfinstall

Run dpkg -i helpers/bat*.deb

RUN echo "Installing powershell" \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --yes --dearmor --output /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/microsoft-debian-bullseye-prod bullseye main" > /etc/apt/sources.list.d/microsoft.list \
    && apt-get update && apt-get install -y powershell

COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

ENTRYPOINT ["/root/entrypoint.sh"]


