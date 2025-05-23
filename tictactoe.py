#inicializando o jogo criando um objeto jogo com o layout e os jogadores.
class table():
        matriz= [
            ['0', '1', '2'],
            ['3', '4', '5'],
            ['6', '7', '8'],
        ]
        player1='x'
        player2='o'
        turn=player1
        on=True


reset= [
    ['0', '1', '2'],
    ['3', '4', '5'],
    ['6', '7', '8'],
]
jogo = table()


def game(table):
    while table.on is True:
            posicao=999
            for row in range(3):
                print(table.matriz[row])
            if table.turn == 'x':
                while posicao not in range(0,8):
                    print('Player 1 where do you want to play?')
                    posicao=int(input())
                linha=int(posicao/len(table.matriz))
                coluna=int(posicao%len(table.matriz))
                table.matriz[linha][coluna]=table.turn
                table.turn=table.player2
            else:
                while posicao not in range(0, 8):
                    print('Player 2 where do you want to play?')
                    posicao = int(input())
                linha=int(posicao/len(table.matriz))
                coluna=int(posicao%len(table.matriz))
                table.matriz[linha][coluna]=table.turn
                table.turn=table.player1

            for row in range(3):
                if table.matriz[row][0] == table.matriz[row][1] and table.matriz[row][1] == table.matriz[row][2]:
                    print(f'{table.turn} loses')
                    table.on = False
                if table.matriz[0][row] == table.matriz[1][row] and table.matriz[1][row] == table.matriz[2][row]:
                    print(f'{table.turn} loses')
                    table.on = False
                if table.matriz[0][0] == table.matriz[1][1] and table.matriz[1][1] == table.matriz[2][2]:
                    print(f'{table.turn} loses')
                    table.on = False
                if table.matriz[2][0] == table.matriz[1][1] and table.matriz[1][1] == table.matriz[0][2]:
                    print(f'{table.turn} loses')
                    table.on = False
            if table.on is False:
                while True:
                    user_input = input("Do you want to continue? (yes/no): ")
                    if user_input.lower() in ["yes", "y"]:
                        print("Continuing...")
                        table.on=True
                        table.matriz=reset
                        break
                    elif user_input.lower() in ["no", "n"]:
                        print("Exiting...")
                        break
                    else:
                        print("Invalid input. Please enter yes/no.")
game(jogo)
